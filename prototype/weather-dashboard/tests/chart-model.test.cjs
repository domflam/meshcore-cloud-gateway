const assert = require('node:assert/strict');
const model = require('../static/chart-model.js');
const row=(minute, value, simulated=true)=>({observed_at:`2026-11-03T13:${String(minute).padStart(2,'0')}:00Z`,wind_speed_mps:value,humidity_pct:value,pressure_hpa:value,temperature_c:value,wind_simulated:simulated});
for(const field of ['temperature_c','humidity_pct','pressure_hpa','wind_speed_mps']) {
  const result=model([row(1,0),row(2,null),row(3,1)],field);
  assert.equal(result.points.length,2);
  assert.equal(result.points[0].value,0);
  assert.equal(result.points[1].breakBefore,true);
  assert.equal(result.min,0);
  assert.equal(result.max,1);
  assert.equal(model([row(1,NaN),row(2,'2')],field).points.length,0);
}
const wind=model([row(1,0),row(2,0)],'wind_speed_mps',{floor:0,padding:.3});
assert.equal(wind.low,0);assert.ok(wind.high>0);assert.equal(wind.points[1].breakBefore,false);
assert.equal(model([row(1,0,true),row(2,0,false)],'wind_speed_mps').points[1].breakBefore,true);
const humidity=model([row(1,100),row(2,100)],'humidity_pct',{floor:0,ceiling:100,padding:1});
assert.equal(humidity.high,100);assert.ok(humidity.low<100);
assert.equal(model([],'temperature_c').min,null);
console.log('Chart model: missing values, real/simulated zero, series boundaries and four measurements verified.');
