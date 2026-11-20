"""Run actual station parsing, NVS codec, HTTP handlers and scheduler in C++."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StationsTests(unittest.TestCase):
    def compile_run(self, source, extra_headers=None):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, content in (extra_headers or {}).items():
                (tmp / name).write_text(content)
            (tmp / 'test.cpp').write_text(source)
            subprocess.run([compiler, '-std=c++11', '-Wall', '-Wextra', '-Werror',
                            '-I'+str(tmp), '-I'+str(ROOT/'tests/firmware_mocks'),
                            '-I'+str(ROOT/'firmware/include'), str(tmp/'test.cpp'),
                            '-o', str(tmp/'test')], check=True, capture_output=True, text=True)
            subprocess.run([str(tmp/'test')], check=True)

    def test_config_validation_and_versioned_round_trip(self):
        self.compile_run(r'''
#include "StationConfig.h"
#include <cassert>
#include <initializer_list>
using namespace gateway_stations;
int main(){
 Configuration c; c.stations[0].enabled=true;
 strcpy(c.stations[0].node_id,"RAK4631-LAB"); strcpy(c.stations[0].label,"Maison");
 assert(parseKey("9222cc51c4ad973798dab0e1e5d49630948a6e1f0b3576a059774e1d0d53ebb7",c.stations[0].public_key));
 c.stations[0].profile=cloud_gateway::rak4631RealWindProfile();
 c.stations[1]=c.stations[0]; strcpy(c.stations[1].node_id,"RAK4631-CLUB");
 assert(validate(c)); // same public key, even with different names
 c.stations[1].public_key[0]++;
 assert(!validate(c));
 uint8_t bytes[kBlobSize]; assert(encode(c,bytes,sizeof bytes));
 Configuration restored; assert(decode(bytes,sizeof bytes,restored));
 assert(restored.stations[1].enabled && !strcmp(restored.stations[1].node_id,"RAK4631-CLUB"));
 assert(restored.stations[1].profile.wind_channel==3 && !restored.stations[1].profile.wind_simulated);
 bytes[30]^=1; assert(!decode(bytes,sizeof bytes,restored)); bytes[30]^=1;
 assert(!decode(bytes,sizeof bytes-1,restored)); bytes[4]=2; assert(!decode(bytes,sizeof bytes,restored));
 int channel=5;
 for(const char* s:{"", "-2", "256", "1.0", "2x", "+2", " 2", "999999999999999999"}) assert(!parseChannel(s,channel));
 assert(parseChannel("-1",channel)&&channel==-1);assert(parseChannel("255",channel)&&channel==255);
 uint8_t key[32]; memset(key,42,32);
 for(const char* bad:{"00", "zz222cc51c4ad973798dab0e1e5d49630948a6e1f0b3576a059774e1d0d53ebb7",
 "0000000000000000000000000000000000000000000000000000000000000000",
 "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"}) {assert(!parseKey(bad,key));assert(key[0]==42);}
 strcpy(c.stations[1].node_id,c.stations[0].node_id); assert(validate(c));
 strcpy(c.stations[1].node_id,"club with spaces"); assert(validate(c));
 memset(c.stations[1].node_id,'a',64);c.stations[1].node_id[64]=0;assert(!validate(c));
 c.stations[1].profile.wind_channel=-1;c.stations[1].profile.wind_simulated=true;assert(validate(c));
}
''')

    def test_two_station_fairness_timeouts_and_disabled_slots(self):
        self.compile_run(r'''
#include "TelemetryScheduler.h"
#include <cassert>
using namespace cloud_gateway;
int main(){
 uint8_t a[32]={1},b[32]={2}; PollTarget t[2]={{"a",a,32,true},{"b",b,32,true}};
 TelemetryScheduler q(t,2,600000,30000);
 assert(!q.next(0,true)); assert(q.next(0,false)==t);q.markSent(0,11);
 assert(!q.next(10,false));assert(!q.markReply(10,12));assert(!q.tick(29999));
 assert(q.tick(30000));assert(q.next(30000,false)==t+1);q.markSent(30000,12);
 assert(q.markReply(30001,12));assert(!q.next(630000,false));assert(q.next(630001,false)==t);
 q.skip(630001);assert(q.next(630001,false)==t+1); // missing contact on a
 q.skip(630001);assert(!q.next(630002,false)); // immediate send failure on b
 t[0].enabled=false;assert(q.next(1230001,false)==t+1);q.markSent(1230001,13);
 q.pauseForCompanion(1230002);assert(!q.markReply(1230003,13));
 t[1].enabled=false;assert(!q.next(1830002,false));assert(!q.next(1830003,false));
 t[0].enabled=true;assert(q.next(2430002,false)==t); // slot 2 still disabled
 q.markSent(2430002,14);q.markReply(2430003,14);assert(!q.next(2430004,false));
 TelemetryScheduler wrap(t,2,600000,30000);wrap.next(0xfffffff0UL,false);wrap.markSent(0xfffffff0UL,15);
 assert(wrap.tick(uint32_t(0xfffffff0UL+30000UL)));
}
''')

    def test_admin_handlers_persistence_migration_and_atomic_rejection(self):
        self.compile_run(r'''
#define GATEWAY_STATIONS_DEFINE_STORAGE
#include "GatewayStationPortal.h"
#include <cassert>
MockSerial Serial;
std::map<std::string,std::vector<uint8_t>> nvs;
bool fail_write=false;
using namespace gateway_stations;
int main(){
 begin();assert(active.stations[0].enabled);assert(!active.stations[1].enabled);
 assert(!strcmp(active.stations[0].node_id,"RAK4631-LAB"));assert(nvs.empty());
 nvs["gateway-cloud/token"]={1,2,3};nvs["gateway-cloud/ca"]={4,5,6};nvs["gateway-wifi/ssid"]={7,8,9};
 WebServer portal;gateway_station_portal::routes(portal);
 portal.request("/stations",HTTP_GET);assert(portal.code==200);assert(portal.body.value.find("RAK4631-LAB")!=std::string::npos);
 auto fields=[&](int i,const char* id,const char* key,bool enabled){
  std::string p="s"+std::to_string(i)+"_";
  portal.args[p+"id"]=id;portal.args[p+"label"]="Club < & ' test";portal.args[p+"key"]=key;
  portal.args[p+"enabled"]=enabled?"1":"";
  portal.args[p+"voltage"]="1";portal.args[p+"temperature"]="2";portal.args[p+"humidity"]="2";
  portal.args[p+"pressure"]="2";portal.args[p+"wind"]="3";portal.args[p+"padding"]="1";
 };
 fields(0,"RAK4631-LAB","1111111111111111111111111111111111111111111111111111111111111111",true);
 fields(1,"RAK4631-CLUB","2222222222222222222222222222222222222222222222222222222222222222",true);
 portal.request("/stations/save",HTTP_POST);assert(portal.code==200);
 assert(active.stations[1].enabled==false); // apply only after reboot
 auto before=nvs;Configuration saved;assert(load(saved)==LoadStatus::Loaded);
 assert(saved.stations[1].enabled);assert(saved.stations[1].profile.temperature_channel==2);
 assert((nvs["gateway-cloud/token"]==std::vector<uint8_t>{1,2,3}));
 assert((nvs["gateway-cloud/ca"]==std::vector<uint8_t>{4,5,6}));
 assert((nvs["gateway-wifi/ssid"]==std::vector<uint8_t>{7,8,9}));
 portal.request("/stations",HTTP_GET);assert(portal.body.value.find("Club &lt; &amp; &#39; test")!=std::string::npos);
 portal.args["s1_id"]="RAK4631-LAB";portal.request("/stations/save",HTTP_POST);assert(portal.code==400 && before==nvs);
 portal.args["s1_id"]="RAK4631-CLUB";portal.args["s1_key"]=portal.args["s0_key"];
 portal.request("/stations/save",HTTP_POST);assert(portal.code==400 && before==nvs);
 fields(1,"RAK4631-CLUB","2222222222222222222222222222222222222222222222222222222222222222",true);
 portal.args["s1_temperature"]="2oops";portal.request("/stations/save",HTTP_POST);assert(portal.code==400 && before==nvs);
 portal.args["s1_temperature"]="2";fail_write=true;
 portal.request("/stations/save",HTTP_POST);assert(portal.code==503 && before==nvs);fail_write=false;
 begin();assert(active.stations[1].enabled && !strcmp(active.stations[1].node_id,"RAK4631-CLUB"));
 // Corrupt persisted configuration disables polling instead of silently reverting to a different identity.
 nvs["gateway-nodes/config"][10]^=1;begin();assert(storage_error && !active.stations[0].enabled && !active.stations[1].enabled);
}
''', {'GatewayStationDefaults.h': '''#pragma once
namespace gateway_stations { inline Station buildDefaultStation(){Station s;s.enabled=true;
strcpy(s.node_id,"RAK4631-LAB");memset(s.public_key,1,32);s.profile=cloud_gateway::rak4631RealWindProfile();return s;} }
'''})
