# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.hr_attendance.controllers.main import HrAttendance as HrAttendanceController
import logging

_logger = logging.getLogger(__name__)


class HrAttendanceCtrlController(HrAttendanceController):
    """Keep browser coordinates for office-polygon resolution.

    Odoo 19's standard ``_get_geoip_response`` discards latitude and
    longitude when company device tracking is disabled.  The office label can
    still resolve a polygon in that situation, but the attendance record then
    receives no coordinates.  Redeclaring the route preserves Odoo's normal
    response and access checks while retaining coordinates supplied by our
    frontend.
    """

    @http.route('/hr_attendance/systray_check_in_out', type='jsonrpc', auth='user')
    def systray_attendance(self, latitude=False, longitude=False):
        employee = request.env.user.employee_id
        was_checked_in = employee.attendance_state == 'checked_in'
        attendance = employee.last_attendance_id if was_checked_in else False

        # Let the installed Odoo 19 revision perform its standard check-in/out
        # and build the response expected by the OWL attendance menu.
        result = super().systray_attendance(
            latitude=latitude,
            longitude=longitude,
        )

        # Some Odoo 19 revisions discard coordinates when company device
        # tracking is disabled. Persist the coordinates supplied by this
        # module after the standard operation, without relying on private
        # controller helpers whose names differ between revisions.
        if latitude not in (False, None) and longitude not in (False, None):
            if not attendance:
                attendance = request.env['hr.attendance'].search(
                    [('employee_id', '=', employee.id)],
                    order='check_in desc, id desc',
                    limit=1,
                )
            if attendance:
                coordinate_vals = (
                    {
                        'out_latitude': latitude,
                        'out_longitude': longitude,
                    }
                    if was_checked_in
                    else {
                        'in_latitude': latitude,
                        'in_longitude': longitude,
                    }
                )
                # A regular employee can use the systray endpoint but does not
                # necessarily have direct write ACL on hr.attendance. The
                # record is restricted to the authenticated user's employee
                # before this narrowly scoped sudo write.
                if attendance.employee_id == employee:
                    attendance.sudo().write(coordinate_vals)

        return result

class AttendanceLocationController(http.Controller):
    @http.route('/attendance_ctrl/get_name', type='jsonrpc', auth='user')
    def get_office_name(self, latitude, longitude):
        # Normalize numeric types for coordinates
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except Exception:
            latitude = float(latitude or 0)
            longitude = float(longitude or 0)
        """
        Mengembalikan nama office.location yang terdekat,
        atau 'Outside Office' jika tidak ada yang memenuhi radius.
        """
        # Normalize types
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except Exception:
            latitude = float(latitude or 0)
            longitude = float(longitude or 0)
        cr = request.env.cr
        nama = None
        try:
            cr.execute(
        """
        SELECT name
        FROM office_location
        WHERE the_geom2 IS NOT NULL
          AND ST_IsValid(the_geom2)
          AND (
                ST_Covers(
                    the_geom2,
                    ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857)
                )
                OR ST_DWithin(
                    the_geom2,
                    ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857),
                    5
                )
          )
        ORDER BY id
        LIMIT 1
        """, (float(longitude), float(latitude), float(longitude), float(latitude)),
            )
            row = cr.fetchone()
            if row:
                nama = row[0]
        except Exception as e:
                _logger.warning("get_name polygon lookup failed: %s", e)
        return {'location': nama or 'Outside Office', 'latitude': latitude, 'longitude': longitude}


class AttendanceLocationMapEditor(http.Controller):
    @http.route('/attendance_ctrl/map_editor', type='http', auth='user')
    def map_editor(self, **kw):
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            return request.not_found()
        html = r"""<!DOCTYPE html>
<html><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1.0'/>
<title>Polygon Editor</title>
<style>
html,body,#map{height:100%;margin:0;overflow:hidden;font-family:Arial,sans-serif}#map{position:relative;background:#ddd}
#tiles{position:absolute;inset:0;overflow:hidden}.tile{position:absolute;width:256px;height:256px;pointer-events:none}.overlay{position:absolute;inset:0;width:100%;height:100%;cursor:crosshair;touch-action:none;pointer-events:all;user-select:none}
.toolbar{position:absolute;z-index:10;top:10px;left:10px;background:#fff;padding:8px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.toolbar button{margin-right:5px}.hint{font-size:12px;margin-top:6px;color:#555}.attribution{position:absolute;right:4px;bottom:2px;background:#fff9;font-size:11px;padding:2px 4px}
</style>
</head><body>
<div id='map'></div>
<div class='toolbar'>
  <button id='btnUse'>Use Polygon</button><button id='btnUndo'>Undo</button><button id='btnClear'>Clear</button>
  <button id='btnMinus'>−</button><button id='btnPlus'>+</button><button id='btnGps'>My Location</button>
  <div class='hint'>Click the map to add polygon points.</div>
</div>
<script>(function(){
var map=document.getElementById('map'),tiles=document.createElement('div'),svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
tiles.id='tiles';svg.setAttribute('class','overlay');map.appendChild(tiles);map.appendChild(svg);
var attr=document.createElement('div');attr.className='attribution';attr.innerHTML='&copy; OpenStreetMap contributors';map.appendChild(attr);
var center={lat:-6.200,lon:106.816},zoom=16,points=[],drag=null;
function world(lat,lon,z){var s=256*Math.pow(2,z),x=(lon+180)/360*s,rad=lat*Math.PI/180,y=(1-Math.log(Math.tan(rad)+1/Math.cos(rad))/Math.PI)/2*s;return{x:x,y:y};}
function geo(x,y,z){var s=256*Math.pow(2,z),lon=x/s*360-180,n=Math.PI-2*Math.PI*y/s,lat=180/Math.PI*Math.atan(.5*(Math.exp(n)-Math.exp(-n)));return{lat:lat,lon:lon};}
function project(p){var c=world(center.lat,center.lon,zoom),w=world(p.lat,p.lon,zoom);return{x:map.clientWidth/2+w.x-c.x,y:map.clientHeight/2+w.y-c.y};}
function unproject(x,y){var c=world(center.lat,center.lon,zoom);return geo(c.x+x-map.clientWidth/2,c.y+y-map.clientHeight/2,zoom);}
function render(){tiles.innerHTML='';var c=world(center.lat,center.lon,zoom),left=c.x-map.clientWidth/2,top=c.y-map.clientHeight/2,minX=Math.floor(left/256),maxX=Math.floor((left+map.clientWidth)/256),minY=Math.floor(top/256),maxY=Math.floor((top+map.clientHeight)/256),n=Math.pow(2,zoom);for(var x=minX;x<=maxX;x++){for(var y=minY;y<=maxY;y++){if(y<0||y>=n)continue;var img=document.createElement('img');img.className='tile';img.alt='';img.src='https://tile.openstreetmap.org/'+zoom+'/'+((x%n+n)%n)+'/'+y+'.png';img.style.left=(x*256-left)+'px';img.style.top=(y*256-top)+'px';tiles.appendChild(img);}}svg.innerHTML='';var hit=document.createElementNS(svg.namespaceURI,'rect');hit.setAttribute('x','0');hit.setAttribute('y','0');hit.setAttribute('width','100%');hit.setAttribute('height','100%');hit.setAttribute('fill','transparent');hit.setAttribute('pointer-events','all');svg.appendChild(hit);if(points.length){var xy=points.map(project),poly=document.createElementNS(svg.namespaceURI,'polygon');poly.setAttribute('points',xy.map(function(p){return p.x+','+p.y}).join(' '));poly.setAttribute('fill','#714b6766');poly.setAttribute('stroke','#714b67');poly.setAttribute('stroke-width','3');svg.appendChild(poly);xy.forEach(function(p){var c=document.createElementNS(svg.namespaceURI,'circle');c.setAttribute('cx',p.x);c.setAttribute('cy',p.y);c.setAttribute('r','5');c.setAttribute('fill','#fff');c.setAttribute('stroke','#714b67');svg.appendChild(c);});}}
function beginDrag(x,y){drag={x:x,y:y,lastX:x,lastY:y,start:world(center.lat,center.lon,zoom),moved:false};svg.style.cursor='grabbing';}
function moveDrag(x,y){if(!drag)return;drag.lastX=x;drag.lastY=y;var dx=x-drag.x,dy=y-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)drag.moved=true;if(drag.moved){center=geo(drag.start.x-dx,drag.start.y-dy,zoom);render();}}
function finishDrag(){if(!drag)return;var state=drag;drag=null;svg.style.cursor='crosshair';if(!state.moved){points.push(unproject(state.lastX,state.lastY));render();}}
svg.addEventListener('mousedown',function(ev){if(ev.button!==0)return;ev.preventDefault();beginDrag(ev.clientX,ev.clientY);});
window.addEventListener('mousemove',function(ev){if(!drag)return;ev.preventDefault();moveDrag(ev.clientX,ev.clientY);});
window.addEventListener('mouseup',function(ev){if(ev.button===0)finishDrag();});
svg.addEventListener('touchstart',function(ev){if(ev.touches.length!==1)return;ev.preventDefault();var t=ev.touches[0];beginDrag(t.clientX,t.clientY);},{passive:false});
window.addEventListener('touchmove',function(ev){if(!drag||ev.touches.length!==1)return;ev.preventDefault();var t=ev.touches[0];moveDrag(t.clientX,t.clientY);},{passive:false});
window.addEventListener('touchend',function(){finishDrag();});window.addEventListener('touchcancel',function(){drag=null;svg.style.cursor='crosshair';});
svg.addEventListener('wheel',function(ev){ev.preventDefault();zoom=Math.max(2,Math.min(19,zoom+(ev.deltaY<0?1:-1)));render();},{passive:false});
document.getElementById('btnClear').onclick=function(){points=[];render();};document.getElementById('btnUndo').onclick=function(){points.pop();render();};
document.getElementById('btnPlus').onclick=function(){zoom=Math.min(19,zoom+1);render();};document.getElementById('btnMinus').onclick=function(){zoom=Math.max(2,zoom-1);render();};
document.getElementById('btnGps').onclick=function(){navigator.geolocation&&navigator.geolocation.getCurrentPosition(function(p){center={lat:p.coords.latitude,lon:p.coords.longitude};render();});};
document.getElementById('btnUse').onclick=function(){if(points.length<3){alert('Add at least three polygon points.');return;}var coords=points.map(function(p){return p.lon.toFixed(7)+' '+p.lat.toFixed(7)});coords.push(coords[0]);window.parent.postMessage({type:'odoo-geom-wkt',wkt:'POLYGON(('+coords.join(', ')+'))'},window.location.origin);};
window.addEventListener('message', function(ev){
  try{
    if(ev.origin!==window.location.origin)return;
    var data = ev && ev.data;
    if (!data || data.type !== 'odoo-geom-wkt-init' || !data.wkt) return;
    var text = String(data.wkt || '').trim();
    if (!/^POLYGON\s*\(\(/i.test(text)) return;
    var inside = text.replace(/^POLYGON\s*\(\(/i,'').replace(/\)\)\s*$/,'');
    var pts = inside.split(',');
    var coords = [];
    for (var i=0;i<pts.length;i++){
      var p = pts[i].trim().split(/\s+/);
      if (p.length>=2){
        var lon = parseFloat(p[0]), lat = parseFloat(p[1]);
        if (!isNaN(lat) && !isNaN(lon)) coords.push([lat, lon]);
      }
    }
    if (coords.length){points=coords.map(function(p){return{lat:p[0],lon:p[1]};});center=points[0];render();}
  }catch(e){ /* debug only  */ }
});
window.addEventListener('resize',render);render();
})();</script>
</body></html>"""
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
