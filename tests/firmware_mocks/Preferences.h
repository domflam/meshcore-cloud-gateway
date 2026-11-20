#pragma once
#include "Arduino.h"
#include <map>
#include <vector>
extern std::map<std::string,std::vector<uint8_t>> nvs;
extern bool fail_write;
class Preferences {
  std::string prefix;
 public:
  bool begin(const char* name,bool readOnly){prefix=std::string(name)+"/";return !readOnly || nvs.count(prefix+"config");}
  void end(){}
  bool isKey(const char* key){return nvs.count(prefix+key);}
  size_t getBytesLength(const char* key){return nvs.at(prefix+key).size();}
  size_t getBytes(const char* key,void* out,size_t count){const auto& v=nvs.at(prefix+key);size_t len=v.size()<count?v.size():count;memcpy(out,v.data(),len);return len;}
  size_t putBytes(const char* key,const void* in,size_t count){if(fail_write)return 0;const auto* p=(const uint8_t*)in;nvs[prefix+key]=std::vector<uint8_t>(p,p+count);return count;}
};
