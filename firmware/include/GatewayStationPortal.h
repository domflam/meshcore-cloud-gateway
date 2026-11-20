#pragma once
#include <WebServer.h>
#include "GatewayStations.h"

namespace gateway_station_portal {
static String escape(String text) {
  text.replace("&","&amp;"); text.replace("<","&lt;"); text.replace(">","&gt;");
  text.replace("\"","&quot;"); text.replace("'","&#39;"); return text;
}
static String keyText(const uint8_t* key) {
  bool any=false; for(size_t i=0;i<32;++i) any |= key[i]!=0;
  if(!any) return "";
  char hex[65]; const char* digits="0123456789abcdef";
  for(size_t i=0;i<32;++i) { hex[2*i]=digits[key[i]>>4]; hex[2*i+1]=digits[key[i]&15]; }
  hex[64]=0; return String(hex);
}
static void textInput(String& page,const String& prefix,const char* name,const char* label,
                      const String& value,unsigned maxLength) {
  page+="<p><label>"+String(label)+" <input name='"+prefix+name+"' maxlength='"+String(maxLength)+
        "' value='"+escape(value)+"'></label></p>";
}
static void routes(WebServer& portal) {
  portal.on("/stations",HTTP_GET,[&portal]() {
    gateway_stations::Configuration config=gateway_stations::active;
    const auto status=gateway_stations::load(config);
    String page; page.reserve(10000);
    page="<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         "<title>Stations météo</title><style>body{font-family:system-ui;max-width:720px;margin:24px auto;padding:0 16px}"
         "fieldset{margin:20px 0;padding:16px}input{max-width:100%}input[type=number]{width:75px}"
         "input[name$=_key]{width:100%;font-family:monospace}button{padding:12px}</style>"
         "<h1>Stations météo</h1><p>Deux stations interrogées successivement. Les modifications prennent effet après redémarrage.</p>"
         "<p>L'identifiant est envoyé à GCP comme node_id : conservez-le pour préserver l'historique de cette station.</p>";
    if(status==gateway_stations::LoadStatus::Invalid ||
       (gateway_stations::storage_error && status!=gateway_stations::LoadStatus::Loaded))
      page+="<p><strong>Configuration enregistrée illisible. Corrigez et enregistrez les stations avant de redémarrer.</strong></p>";
    page+="<form method='POST' action='/stations/save'>";
    for(size_t i=0;i<gateway_stations::kStationCount;++i) {
      const auto& s=config.stations[i]; const auto& p=s.profile;
      String prefix="s"+String(unsigned(i))+"_";
      page+="<fieldset><legend>Station "+String(unsigned(i+1))+"</legend><label><input type='checkbox' name='"+prefix+"enabled' value='1'";
      if(s.enabled) page+=" checked";
      page+=">Activer cette station</label>";
      textInput(page,prefix,"label","Nom affiché",s.label,48);
      textInput(page,prefix,"id","Identifiant stable (node_id)",s.node_id,64);
      textInput(page,prefix,"key","Clé publique MeshCore (64 caractères hexadécimaux)",keyText(s.public_key),64);
      page+="<p><label>Préréglage <select onchange=\"preset(this,'"+prefix+"')\">"
            "<option value=''>Configuration ci-dessous</option><option value='legacy'>GAT562 historique</option>"
            "<option value='real'>RAK4631 — vent réel</option><option value='sim'>RAK4631 — vent simulé</option></select></label></p>"
            "<p>Canaux propres à ce matériel. -1 désactive une mesure.</p>";
      const int values[]={p.voltage_channel,p.temperature_channel,p.humidity_channel,p.pressure_channel,p.wind_channel};
      const char* names[]={"voltage","temperature","humidity","pressure","wind"};
      const char* labels[]={"Tension","Température","Humidité","Pression","Vent (entrée analogique en m/s)"};
      for(size_t j=0;j<5;++j)
        page+="<p><label>"+String(labels[j])+" <input type='number' name='"+prefix+names[j]+"' required min='-1' max='255' value='"+String(values[j])+"'></label></p>";
      page+="<p><label><input type='checkbox' name='"+prefix+"simulated' value='1'";
      if(p.wind_simulated) page+=" checked";
      page+=">Vent simulé (uniquement une valeur zéro)</label></p>";
      page+="<details><summary>Fin de trame</summary><label>Nombre d'octets nuls autorisés <input type='number' name='"+prefix+
            "padding' required min='0' max='4' value='"+String(unsigned(p.trailing_zero_padding_bytes))+"'></label>"
            "<p>Préréglages : GAT562 = 4, RAK = 1.</p></details></fieldset>";
    }
    page+="<button>Enregistrer les deux stations</button></form>"
          "<p>Chaque station doit aussi être présente dans les contacts MeshCore de la passerelle."
          " Aucun changement GCP, Wi-Fi, token ou certificat n'est effectué ici.</p><p><a href='/'>Retour</a></p>"
          "<script>function preset(sel,p){if(!sel.value)return;const f=sel.form;const r=sel.value!='legacy';"
          "const v=r?[1,2,2,2,3]:[1,1,-1,-1,-1];['voltage','temperature','humidity','pressure','wind'].forEach((n,i)=>f.elements[p+n].value=v[i]);"
          "f.elements[p+'padding'].value=r?1:4;f.elements[p+'simulated'].checked=sel.value=='sim';}</script></html>";
    portal.sendHeader("Cache-Control","no-store");
    portal.send(200,"text/html; charset=utf-8",page);
  });
  portal.on("/stations/save",HTTP_POST,[&portal]() {
    gateway_stations::Configuration config;
    for(size_t i=0;i<gateway_stations::kStationCount;++i) {
      auto& s=config.stations[i]; auto& p=s.profile; String prefix="s"+String(unsigned(i))+"_";
      String id=portal.arg(prefix+"id"), label=portal.arg(prefix+"label"), key=portal.arg(prefix+"key");
      id.trim(); label.trim(); key.trim();
      if(id.length()>64 || label.length()>48 || (key.length() && !gateway_stations::parseKey(key.c_str(),s.public_key))) {
        portal.send(400,"text/plain; charset=utf-8","Identifiant, nom ou clé publique invalide. Rien n'a été enregistré."); return;
      }
      memcpy(s.node_id,id.c_str(),id.length()+1); memcpy(s.label,label.c_str(),label.length()+1);
      s.enabled=portal.arg(prefix+"enabled")=="1";
      int* fields[]={&p.voltage_channel,&p.temperature_channel,&p.humidity_channel,&p.pressure_channel,&p.wind_channel};
      const char* names[]={"voltage","temperature","humidity","pressure","wind"};
      for(size_t j=0;j<5;++j) {
        if(!gateway_stations::parseChannel(portal.arg(prefix+names[j]).c_str(),*fields[j])) {
          portal.send(400,"text/plain; charset=utf-8","Canal invalide. Rien n'a été enregistré."); return;
        }
      }
      int padding=0;
      if(!gateway_stations::parseChannel(portal.arg(prefix+"padding").c_str(),padding) || padding<0 || padding>4) {
        portal.send(400,"text/plain","Fin de trame invalide"); return;
      }
      p.trailing_zero_padding_bytes=size_t(padding); p.wind_simulated=portal.arg(prefix+"simulated")=="1";
    }
    const char* error=gateway_stations::validate(config);
    if(error) { portal.send(400,"text/plain; charset=utf-8",String(error)+". Rien n'a été enregistré."); return; }
    if(!gateway_stations::save(config)) { portal.send(503,"text/plain","Enregistrement impossible; reessayez."); return; }
    portal.send(200,"text/html; charset=utf-8","<meta charset='utf-8'><h2>Stations enregistrées</h2><p>Redémarrez la passerelle pour appliquer.</p><a href='/stations'>Revoir les stations</a>");
  });
}
} // namespace gateway_station_portal
