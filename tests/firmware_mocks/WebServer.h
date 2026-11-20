#pragma once
#include "Arduino.h"
#include <map>
#include <functional>
static constexpr int HTTP_GET=0,HTTP_POST=1;
class WebServer {
 public:
  std::map<std::pair<std::string,int>,std::function<void()>> handlers;
  std::map<std::string,String> args;
  int code=0; String body;
  void on(const char* url,int method,std::function<void()> fn){handlers[{url,method}]=fn;}
  String arg(const String& key){auto it=args.find(key.value);return it==args.end()?String(""):it->second;}
  void send(int status,const char*,const String& content){code=status;body=content;}
  void sendHeader(const char*,const char*){}
  void request(const char* url,int method){handlers.at({url,method})();}
};
