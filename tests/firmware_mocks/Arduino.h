#pragma once
#include <string>
#include <cstring>
#include <cstdint>
#include <cstdarg>
class String {
 public:
  std::string value;
  String()=default;
  String(const char* s):value(s?s:""){}
  String(std::string s):value(s){}
  String(int n):value(std::to_string(n)){}
  String(unsigned n):value(std::to_string(n)){}
  const char* c_str() const{return value.c_str();}
  size_t length() const{return value.size();}
  void reserve(size_t n){value.reserve(n);}
  void trim(){auto a=value.find_first_not_of(" \r\n\t"),b=value.find_last_not_of(" \r\n\t");value=a==std::string::npos?"":value.substr(a,b-a+1);}
  void replace(const String& from,const String& to){size_t p=0;while((p=value.find(from.value,p))!=std::string::npos){value.replace(p,from.length(),to.value);p+=to.length();}}
  String& operator+=(const String& b){value+=b.value;return *this;}
  friend String operator+(const String& a,const String& b){return String(a.value+b.value);}
  friend bool operator==(const String& a,const String& b){return a.value==b.value;}
};
struct MockSerial { void println(const String&){} void printf(const char*,...){} };
extern MockSerial Serial;
