const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {selectTheme} = require('../static/theme.js');
assert.equal(selectTheme('dark','light',false),'dark');
assert.equal(selectTheme('light','dark',true),'light');
assert.equal(selectTheme('invalid','dark',false),'dark');
assert.equal(selectTheme(null,null,true),'dark');
assert.equal(selectTheme(null,'invalid',false),'light');
function browser({search='',stored=null,dark=false,blocked=false}={}) {
  const events={}, root={dataset:{}}, button={hidden:true,setAttribute(k,v){this[k]=v;},addEventListener(k,fn){events[k]=fn;}}, meta={};
  const media={matches:dark,addEventListener(k,fn){events.media=fn;}};
  const window={location:{search,href:'https://weather.test/'+search},document:{documentElement:root,querySelector(){return meta;},getElementById(){return button;},addEventListener(k,fn){events[k]=fn;}},matchMedia(){return media;},localStorage:{getItem(){if(blocked)throw Error();return stored;},setItem(k,v){if(blocked)throw Error();stored=v;}},history:{replaceState(a,b,url){window.location.href=String(url);}}};
  vm.runInNewContext(readFileSync(path.join(__dirname,'../static/theme.js'),'utf8'),{window,URL,URLSearchParams});
  events.DOMContentLoaded(); return {window,root,button,events,meta};
}
const b=browser({search:'?theme=dark&embed=1',stored:'light'});
assert.equal(b.root.dataset.theme,'dark'); assert.equal(b.button.hidden,false);
assert.equal(b.button.textContent,'Mode clair');
b.events.click(); assert.equal(b.root.dataset.theme,'light');
assert.match(b.window.location.href,/theme=light/); assert.match(b.window.location.href,/embed=1/);
assert.equal(b.meta.content,'#f3f4ee');
b.events.media({matches:true});assert.equal(b.root.dataset.theme,'light');
const system=browser({blocked:true});system.events.media({matches:true});assert.equal(system.root.dataset.theme,'dark');
system.events.click();assert.equal(system.root.dataset.theme,'light');
console.log('Theme tests passed: URL precedence, storage, system, toggle, blocked storage and URL preservation');
