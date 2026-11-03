'use strict';
const CACHE='meteo-club-shell-v1';
const SHELL=['/','/static/app.css','/static/app.js','/static/icon.svg','/static/icon-192.png','/static/icon-512.png','/static/icon-maskable-512.png','/manifest.webmanifest'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('meteo-club-shell-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  // Never persist API responses, login requests, cookies or measurements.
  if(event.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
  if(!SHELL.includes(url.pathname))return;
  event.respondWith(fetch(event.request).then(response=>{
    if(response.ok && response.type==='basic'){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)));}
    return response;
  }).catch(()=>caches.match(event.request).then(cached=>cached||Response.error())));
});
