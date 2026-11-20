#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "TelemetryDecoder.h"

namespace gateway_stations {
static constexpr size_t kStationCount = 2;
struct Station {
  bool enabled = false;
  char node_id[65] = {};
  char label[49] = {};
  uint8_t public_key[32] = {};
  cloud_gateway::TelemetryProfile profile;
};
struct Configuration { Station stations[kStationCount]; };
inline int hexDigit(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}
inline bool parseKey(const char* text, uint8_t* key) {
  if (!text || strlen(text) != 64) return false;
  uint8_t parsed[32]; bool any = false, all_ff = true;
  for (size_t i = 0; i < 32; ++i) {
    int a = hexDigit(text[2*i]), b = hexDigit(text[2*i+1]);
    if (a < 0 || b < 0) return false;
    parsed[i] = uint8_t(a*16 + b); any |= parsed[i] != 0; all_ff &= parsed[i] == 255;
  }
  if (!any || all_ff) return false;
  memcpy(key, parsed, 32); return true;
}
inline bool parseChannel(const char* text, int& value) {
  if (!text || !*text) return false;
  if (!strcmp(text, "-1")) { value = -1; return true; }
  unsigned v = 0;
  for (const char* p = text; *p; ++p) {
    if (*p < '0' || *p > '9') return false;
    v = v*10 + unsigned(*p-'0'); if (v > 255) return false;
  }
  value = int(v); return true;
}
inline bool validId(const char* id) {
  size_t len = 0;
  for (; len < 65 && id[len]; ++len) {
    char c = id[len];
    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
          (c >= '0' && c <= '9') || c == '_' || c == '-')) return false;
  }
  return len > 0 && len < 65;
}
inline const char* validate(const Configuration& config) {
  for (size_t i = 0; i < kStationCount; ++i) {
    const auto& s = config.stations[i];
    if (!memchr(s.node_id, 0, sizeof s.node_id) || !memchr(s.label, 0, sizeof s.label))
      return "Texte trop long";
    for (const unsigned char* p = (const unsigned char*)s.label; *p; ++p)
      if (*p < 32 || *p == 127) return "Nom invalide";
    bool any_key = false, all_ff = true;
    for (auto b : s.public_key) { any_key |= b != 0; all_ff &= b == 255; }
    if (s.enabled || s.node_id[0] || any_key) {
      if (!validId(s.node_id)) return "Identifiant requis : 1 a 64 lettres, chiffres, tirets ou underscores";
      if (!any_key || all_ff) return "Cle publique invalide";
    }
    const auto& p = s.profile;
    const int channels[] = {p.voltage_channel,p.temperature_channel,p.humidity_channel,p.pressure_channel,p.wind_channel};
    bool mapped = false;
    for (int c : channels) { if (c < -1 || c > 255) return "Canal invalide"; mapped |= c >= 0; }
    if (s.enabled && !mapped) return "Au moins une mesure doit etre active";
    if (p.trailing_zero_padding_bytes > 4) return "Fin de trame invalide";
    if (p.wind_simulated && p.wind_channel < 0) return "Vent simule sans canal de vent";
  }
  const auto& a=config.stations[0]; const auto& b=config.stations[1];
  if (a.node_id[0] && b.node_id[0] && !strcmp(a.node_id,b.node_id)) return "Les identifiants doivent etre distincts";
  bool a_key=false, b_key=false;
  for(size_t i=0;i<32;++i) { a_key |= a.public_key[i]!=0; b_key |= b.public_key[i]!=0; }
  if (a_key && b_key && !memcmp(a.public_key,b.public_key,32)) return "Les cles publiques doivent etre distinctes";
  return nullptr;
}
// Explicit versioned wire format: no compiler-dependent struct padding in NVS.
static constexpr size_t kBlobSize = 5 + kStationCount*(1+65+49+32+10+1+1) + 4;
inline uint32_t checksum(const uint8_t* bytes, size_t n) {
  uint32_t hash=2166136261UL;
  for(size_t i=0;i<n;++i) hash=(hash ^ bytes[i])*16777619UL;
  return hash;
}
inline bool encode(const Configuration& config, uint8_t* out, size_t size) {
  if (size != kBlobSize || validate(config)) return false;
  memcpy(out,"MCS2",4); out[4]=1; size_t pos=5;
  for (const auto& s: config.stations) {
    out[pos++]=s.enabled;
    memcpy(out+pos,s.node_id,65); pos+=65;
    memcpy(out+pos,s.label,49); pos+=49;
    memcpy(out+pos,s.public_key,32); pos+=32;
    const auto& p=s.profile;
    const int channels[]={p.voltage_channel,p.temperature_channel,p.humidity_channel,p.pressure_channel,p.wind_channel};
    for(int c:channels) { unsigned v=unsigned(c+1); out[pos++]=v&255; out[pos++]=v>>8; }
    out[pos++]=p.wind_simulated; out[pos++]=uint8_t(p.trailing_zero_padding_bytes);
  }
  uint32_t hash=checksum(out,pos);
  for(unsigned i=0;i<4;++i) out[pos++]=uint8_t(hash>>(8*i));
  return true;
}
inline bool decode(const uint8_t* bytes, size_t size, Configuration& result) {
  if(size!=kBlobSize || memcmp(bytes,"MCS2",4) || bytes[4]!=1) return false;
  uint32_t hash=0; for(unsigned i=0;i<4;++i) hash |= uint32_t(bytes[size-4+i])<<(8*i);
  if(hash!=checksum(bytes,size-4)) return false;
  Configuration tmp; size_t pos=5;
  for(auto& s:tmp.stations) {
    if(bytes[pos]>1) return false;
    s.enabled=bytes[pos++];
    memcpy(s.node_id,bytes+pos,65); pos+=65;
    memcpy(s.label,bytes+pos,49); pos+=49;
    memcpy(s.public_key,bytes+pos,32); pos+=32;
    auto& p=s.profile;
    int* channels[]={&p.voltage_channel,&p.temperature_channel,&p.humidity_channel,&p.pressure_channel,&p.wind_channel};
    for(auto c:channels) { unsigned v=bytes[pos] | (unsigned(bytes[pos+1])<<8); pos+=2; if(v>256)return false; *c=int(v)-1; }
    if(bytes[pos]>1) return false;
    p.wind_simulated=bytes[pos++]; p.trailing_zero_padding_bytes=bytes[pos++];
  }
  if(validate(tmp)) return false;
  result=tmp; return true;
}
} // namespace gateway_stations
