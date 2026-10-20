import json
import os
import time
from datetime import date
import requests
from flask import Flask, render_template_string, jsonify, request, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://"
)

CONFIG_FILE = './config.json'

def get_default_dates():
    today = date.today()
    try:
        from_date = today.replace(year=today.year - 5)
    except ValueError:
        from_date = today.replace(year=today.year - 5, day=28)
    return from_date.isoformat(), today.isoformat()

def load_config():
    default = {"url": "", "token": ""}
    if not os.path.exists(CONFIG_FILE):
        return default
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return default
            data = json.loads(content)
            if not isinstance(data, dict):
                return default
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default

def save_config(url, token):
    url = url.rstrip('/')
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"url": url, "token": token}, f)

META_TTL = 300

meta_cache = {
    'data': {
        'correspondents': {},
        'document_types': {},
        'storage_paths': {},
        'tags': {}
    },
    'last_fetch': 0
}

def get_headers():
    conf = load_config()
    return {"Authorization": "Token " + conf.get('token', '')}

def fetch_all_meta(force=False):
    now = time.time()
    if not force and (now - meta_cache['last_fetch']) < META_TTL:
        return
    conf = load_config()
    if not conf.get('url') or not conf.get('token'):
        return
    base = conf['url'] + "/api"
    endpoints = {
        'correspondents': 'correspondents',
        'document_types': 'document_types',
        'storage_paths': 'storage_paths',
        'tags': 'tags'
    }
    for key, endpoint in endpoints.items():
        try:
            r = requests.get(
                base + "/" + endpoint + "/?page_size=1000",
                headers=get_headers(),
                timeout=10
            )
            if r.status_code == 200:
                meta_cache['data'][key] = {
                    item['id']: item['name']
                    for item in r.json().get('results', [])
                }
        except Exception as e:
            print("Meta fetch error (" + key + "): " + str(e))
            meta_cache['data'][key] = {}
    meta_cache['last_fetch'] = time.time()


HTML_TEMPLATE = (
    "<!DOCTYPE html>\n"
    "<html lang=\"en\">\n"
    "<head>\n"
    "<meta charset=\"UTF-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
    "<title>Paperless Export v1.1.7</title>\n"
    "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='style.css') }}\">\n"
    "</head>\n"
    "<body>\n"
    "\n"
    "<!-- Global JS Tooltip -->\n"
    "<div id=\"js-tooltip\"></div>\n"
    "\n"
    "<div class=\"container\">\n"
    "  <div class=\"header\">\n"
    "    <h1 id=\"main-title\"\n"
    "      data-tooltip=\"Version 1.1.7\"\n"
    "      data-tt-class=\"version\"\n"
    "      style=\"cursor:help;\">Paperless-ngx Export</h1>\n"
    "    <div class=\"header-right\">\n"
    "      <span id=\"status\"></span>\n"
    "      <button class=\"btn\" id=\"btn-settings\"\n"
    "        style=\"background:none;font-size:22px;padding:4px;border:1px solid var(--border);border-radius:6px;\">&#9881;</button>\n"
    "    </div>\n"
    "  </div>\n"
    "\n"
    "  <div id=\"progress-bar-wrap\"><div id=\"progress-bar\"></div></div>\n"
    "\n"
    "  <div class=\"filter-section\">\n"
    "    <div class=\"filter-card\">\n"
    "      <div class=\"filter-card-header\"><label id=\"lbl-fulltext\">Full-text search (title + content)</label></div>\n"
    "      <input type=\"text\" id=\"f_query\" placeholder=\"Search term...\" style=\"width:100%;box-sizing:border-box;\">\n"
    "      <div class=\"filter-hint\"></div>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <div class=\"filter-card-header\">\n"
    "        <label id=\"lbl-correspondent\">Correspondent</label>\n"
    "        <button class=\"toggle-mode-btn\" id=\"toggle-corr\" onclick=\"window.toggleMode('corr')\">+ Multi</button>\n"
    "      </div>\n"
    "      <div id=\"wrap-corr\">\n"
    "        <select id=\"f_corr\" class=\"single-select\">\n"
    "          <option value=\"\">-- All --</option>\n"
    "          <option value=\"__empty__\">--- empty ---</option>\n"
    "          {% for cid, name in meta.correspondents.items() %}\n"
    "          <option value=\"{{ cid }}\">{{ name }}</option>\n"
    "          {% endfor %}\n"
    "        </select>\n"
    "      </div>\n"
    "      <div class=\"filter-hint\" id=\"hint-corr\"></div>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <div class=\"filter-card-header\">\n"
    "        <label id=\"lbl-doctype\">Document type</label>\n"
    "        <button class=\"toggle-mode-btn\" id=\"toggle-type\" onclick=\"window.toggleMode('type')\">+ Multi</button>\n"
    "      </div>\n"
    "      <div id=\"wrap-type\">\n"
    "        <select id=\"f_type\" class=\"single-select\">\n"
    "          <option value=\"\">-- All --</option>\n"
    "          <option value=\"__empty__\">--- empty ---</option>\n"
    "          {% for did, name in meta.document_types.items() %}\n"
    "          <option value=\"{{ did }}\">{{ name }}</option>\n"
    "          {% endfor %}\n"
    "        </select>\n"
    "      </div>\n"
    "      <div class=\"filter-hint\" id=\"hint-type\"></div>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <div class=\"filter-card-header\">\n"
    "        <label id=\"lbl-tags\">Tags</label>\n"
    "        <button class=\"toggle-mode-btn\" id=\"toggle-tag\" onclick=\"window.toggleMode('tag')\">+ Multi</button>\n"
    "      </div>\n"
    "      <div id=\"wrap-tag\">\n"
    "        <select id=\"f_tag\" class=\"single-select\">\n"
    "          <option value=\"\">-- All --</option>\n"
    "          <option value=\"__empty__\">--- empty ---</option>\n"
    "          {% for tid, name in meta.tags.items() %}\n"
    "          <option value=\"{{ tid }}\">{{ name }}</option>\n"
    "          {% endfor %}\n"
    "        </select>\n"
    "      </div>\n"
    "      <div class=\"filter-hint\" id=\"hint-tag\"></div>\n"
    "    </div>\n"
    "    <div class=\"filter-card\">\n"
    "      <div class=\"filter-card-header\">\n"
    "        <label id=\"lbl-storagepath\">Storage path</label>\n"
    "        <button class=\"toggle-mode-btn\" id=\"toggle-path\" onclick=\"window.toggleMode('path')\">+ Multi</button>\n"
    "      </div>\n"
    "      <div id=\"wrap-path\">\n"
    "        <select id=\"f_path\" class=\"single-select\">\n"
    "          <option value=\"\">-- All --</option>\n"
    "          <option value=\"__empty__\">--- empty ---</option>\n"
    "          {% for pid, name in meta.storage_paths.items() %}\n"
    "          <option value=\"{{ pid }}\">{{ name }}</option>\n"
    "          {% endfor %}\n"
    "        </select>\n"
    "      </div>\n"
    "      <div class=\"filter-hint\" id=\"hint-path\"></div>\n"
    "    </div>\n"
    "    <div class=\"date-container\">\n"
    "      <div class=\"filter-card\">\n"
    "        <div class=\"filter-card-header\"><label id=\"lbl-datetype\">Filter type</label></div>\n"
    "        <select id=\"f_date_mode\" class=\"date-select\">\n"
    "          <option value=\"created\" id=\"opt-date-created\">Date: Issued</option>\n"
    "          <option value=\"added\" id=\"opt-date-added\">Date: Added</option>\n"
    "        </select>\n"
    "      </div>\n"
    "      <div class=\"filter-card\">\n"
    "        <div class=\"filter-card-header\"><label id=\"lbl-date-from\">From</label></div>\n"
    "        <input type=\"date\" id=\"f_date_gte\" value=\"{{ default_date_from }}\">\n"
    "      </div>\n"
    "      <div class=\"filter-card\">\n"
    "        <div class=\"filter-card-header\"><label id=\"lbl-date-to\">To</label></div>\n"
    "        <input type=\"date\" id=\"f_date_lte\" value=\"{{ default_date_to }}\">\n"
    "      </div>\n"
    "    </div>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"toggles\">\n"
    "    <strong id=\"lbl-visible-cols\">Visible columns:</strong>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(0)\"> <span id=\"tog0\">Issued</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(1)\"> <span id=\"tog1\">Added</span></label>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(2)\"> <span id=\"tog2\">Title</span></label>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(3)\"> <span id=\"tog3\">Correspondent</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(4)\"> <span id=\"tog4\">Tags</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(5)\"> <span id=\"tog5\">Type</span></label>\n"
    "    <label><input type=\"checkbox\" onchange=\"toggleCol(6)\"> <span id=\"tog6\">Path</span></label>\n"
    "    <label><input type=\"checkbox\" checked onchange=\"toggleCol(7)\"> <span id=\"tog7\">Document ID</span></label>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"toolbar\">\n"
    "    <div class=\"toolbar-left\">\n"
    "      <button class=\"btn btn-primary\" id=\"btn-load\" onclick=\"loadDocs()\">Load documents</button>\n"
    "      <button class=\"btn btn-success\" id=\"btn-csv\" onclick=\"exportCSV()\">CSV Export</button>\n"
    "      <button class=\"btn btn-secondary\" id=\"btn-reset\" onclick=\"window.resetFilters()\">&#10005; <span id=\"lbl-reset\">Reset filters</span></button>\n"
    "    </div>\n"
    "    <div class=\"toolbar-right\" id=\"pag-top\">\n"
    "      <span id=\"lbl-per-page-top\">Per page:</span>\n"
    "      <select class=\"page-size-select\" id=\"page-size-top\" onchange=\"setPageSize(this.value)\">\n"
    "        <option value=\"10\">10</option>\n"
    "        <option value=\"25\" selected>25</option>\n"
    "        <option value=\"50\">50</option>\n"
    "        <option value=\"0\" id=\"opt-all-top\">All</option>\n"
    "      </select>\n"
    "      <span class=\"page-info\" id=\"page-info-top\"></span>\n"
    "      <div class=\"page-nav\" id=\"page-nav-top\"></div>\n"
    "    </div>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"table-wrapper\">\n"
    "    <table id=\"target\">\n"
    "      <thead><tr>\n"
    "        <th class=\"c0\" onclick=\"sortTable(0)\"><span id=\"th0\">Issued</span></th>\n"
    "        <th class=\"c1 hidden\" onclick=\"sortTable(1)\"><span id=\"th1\">Added</span></th>\n"
    "        <th class=\"c2\" onclick=\"sortTable(2)\"><span id=\"th2\">Title</span></th>\n"
    "        <th class=\"c3\" onclick=\"sortTable(3)\"><span id=\"th3\">Correspondent</span></th>\n"
    "        <th class=\"c4 hidden\" onclick=\"sortTable(4)\"><span id=\"th4\">Tags</span></th>\n"
    "        <th class=\"c5 hidden\" onclick=\"sortTable(5)\"><span id=\"th5\">Type</span></th>\n"
    "        <th class=\"c6 hidden\" onclick=\"sortTable(6)\"><span id=\"th6\">Path</span></th>\n"
    "        <th class=\"c7\" onclick=\"sortTable(7)\"><span id=\"th7\">Document ID</span></th>\n"
    "      </tr></thead>\n"
    "      <tbody></tbody>\n"
    "    </table>\n"
    "  </div>\n"
    "\n"
    "  <div class=\"pag-right hidden\" id=\"pag-bot\">\n"
    "    <span id=\"lbl-per-page-bot\">Per page:</span>\n"
    "    <select class=\"page-size-select\" id=\"page-size-bot\" onchange=\"setPageSize(this.value)\">\n"
    "      <option value=\"10\">10</option>\n"
    "      <option value=\"25\" selected>25</option>\n"
    "      <option value=\"50\">50</option>\n"
    "      <option value=\"0\" id=\"opt-all-bot\">All</option>\n"
    "    </select>\n"
    "    <span class=\"page-info\" id=\"page-info-bot\"></span>\n"
    "    <div class=\"page-nav\" id=\"page-nav-bot\"></div>\n"
    "  </div>\n"
    "\n"
    "</div>\n"
    "\n"
    "<div id=\"modal\">\n"
    "  <div class=\"modal-content\">\n"
    "    <h3 id=\"modal-title\">API Configuration</h3>\n"
    "    <div class=\"cfg-field\">\n"
    "      <label class=\"cfg-label\" id=\"lbl-url\" for=\"cfg_url\"\n"
    "        data-tooltip=\"Full base URL of your Paperless-ngx instance.&#10;Example: http://192.168.178.102:8010&#10;No trailing slash.\"\n"
    "        data-tt-class=\"\">Paperless-ngx Base URL</label>\n"
    "      <input type=\"text\" id=\"cfg_url\" class=\"cfg-input\"\n"
    "        placeholder=\"http://192.168.178.102:8010\"\n"
    "        value=\"{{ conf.url }}\">\n"
    "      <div class=\"cfg-hint\" id=\"hint-url\">No trailing slash.</div>\n"
    "    </div>\n"
    "    <div class=\"cfg-field\">\n"
    "      <label class=\"cfg-label\" id=\"lbl-token\" for=\"cfg_token\"\n"
    "        data-tooltip=\"The API token is in Paperless-ngx under:&#10;username top right -> Profile -> API Token section.&#10;Copy the full token.\"\n"
    "        data-tt-class=\"\">API Token</label>\n"
    "      <div class=\"token-wrapper\">\n"
    "        <input type=\"password\" id=\"cfg_token\" class=\"cfg-input\"\n"
    "          placeholder=\"Paste API token\"\n"
    "          value=\"{{ conf.token }}\">\n"
    "        <button class=\"token-toggle\" id=\"token_eye\" type=\"button\">Show</button>\n"
    "      </div>\n"
    "      <div class=\"cfg-hint\" id=\"hint-token\">Profile &rarr; API Token</div>\n"
    "    </div>\n"
    "    <div class=\"modal-btn-row\">\n"
    "      <button class=\"btn btn-primary\" id=\"btn-save\" type=\"button\">Save</button>\n"
    "      <button class=\"btn\" style=\"background:#f1f3f4;\" id=\"btn-cancel\" type=\"button\">Cancel</button>\n"
    "    </div>\n"
    "  </div>\n"
    "</div>\n"
    "\n"
    "<script>\n"
    "(function(){\n"
    "\n"
    "var HAS_URL   = {% if conf.url %}true{% else %}false{% endif %};\n"
    "var HAS_TOKEN = {% if conf.token %}true{% else %}false{% endif %};\n"
    "\n"
    "/* =====================================================\n"
    "   JS-TOOLTIP ENGINE\n"
    "   Liest data-tooltip und optionales data-tt-class.\n"
    "   Funktioniert auf ALLEN Elementen inkl. td.\n"
    "   ===================================================== */\n"
    "var ttEl = document.getElementById('js-tooltip');\n"
    "var ttTarget = null;\n"
    "\n"
    "function showTooltip(e, text, cssClass){\n"
    "  ttEl.textContent = text;\n"
    "  ttEl.className = cssClass || '';\n"
    "  ttEl.style.display = 'block';\n"
    "  positionTooltip(e);\n"
    "}\n"
    "\n"
    "function positionTooltip(e){\n"
    "  var x = e.clientX + 14;\n"
    "  var y = e.clientY + 14;\n"
    "  /* Verhindert Abschneiden am rechten Rand */\n"
    "  if(x + 400 > window.innerWidth) x = e.clientX - 420;\n"
    "  if(x < 4) x = 4;\n"
    "  /* Verhindert Abschneiden am unteren Rand */\n"
    "  if(y + 100 > window.innerHeight) y = e.clientY - 80;\n"
    "  if(y < 4) y = 4;\n"
    "  ttEl.style.left = x + 'px';\n"
    "  ttEl.style.top  = y + 'px';\n"
    "}\n"
    "\n"
    "function hideTooltip(){\n"
    "  ttEl.style.display = 'none';\n"
    "  ttEl.className = '';\n"
    "}\n"
    "\n"
    "/* Globaler Listener — delegiert auf alle data-tooltip Elemente */\n"
    "document.addEventListener('mouseover', function(e){\n"
    "  var el = e.target.closest('[data-tooltip]');\n"
    "  if(!el) { hideTooltip(); ttTarget=null; return; }\n"
    "  if(el === ttTarget) return;\n"
    "  ttTarget = el;\n"
    "  var text = el.getAttribute('data-tooltip');\n"
    "  var cls  = el.getAttribute('data-tt-class') || '';\n"
    "  if(text) showTooltip(e, text, cls);\n"
    "});\n"
    "\n"
    "document.addEventListener('mousemove', function(e){\n"
    "  if(ttEl.style.display === 'block') positionTooltip(e);\n"
    "});\n"
    "\n"
    "document.addEventListener('mouseout', function(e){\n"
    "  var el = e.target.closest('[data-tooltip]');\n"
    "  if(!el) return;\n"
    "  var related = e.relatedTarget;\n"
    "  if(related && el.contains(related)) return;\n"
    "  hideTooltip();\n"
    "  ttTarget = null;\n"
    "});\n"
    "\n"
    "var T = {\n"
    "  btn_multi: '+ Multi', btn_single: '- Single',\n"
    "  multi_hint: 'Click to select/deselect - height resizable',\n"
    "  all_option: '-- All --', empty_option: '--- empty ---',\n"
    "  col: ['Issued','Added','Title','Correspondent','Tags','Type','Path','Document ID'],\n"
    "  token_show: 'Show', token_hide: 'Hide',\n"
    "  st_loading: 'Loading documents...', st_page: 'Loading page', st_of: 'of',\n"
    "  st_done: 'documents loaded.', st_error: 'Error loading data!',\n"
    "  page_info: 'Page {cur} of {total} ({count} documents)',\n"
    "  csv_file: 'paperless_export.csv'\n"
    "};\n"
    "\n"
    "var allDocs = [];\n"
    "var currentPage = 1;\n"
    "var pageSize = 25;\n"
    "var multiData = {};\n"
    "var multiMode = {corr:false,type:false,tag:false,path:false};\n"
    "var multiSelected = {corr:{},type:{},tag:{},path:{}};\n"
    "\n"
    "function setPageSize(val){\n"
    "  pageSize=parseInt(val)||0;\n"
    "  document.getElementById('page-size-top').value=String(pageSize);\n"
    "  document.getElementById('page-size-bot').value=String(pageSize);\n"
    "  currentPage=1; renderPage(1);\n"
    "}\n"
    "window.setPageSize=setPageSize;\n"
    "\n"
    "function goToPage(p){\n"
    "  var total=totalPages();\n"
    "  if(p<1||p>total) return;\n"
    "  currentPage=p; renderPage(p);\n"
    "  document.getElementById('pag-top').scrollIntoView({behavior:'smooth',block:'nearest'});\n"
    "}\n"
    "window.goToPage=goToPage;\n"
    "\n"
    "function totalPages(){\n"
    "  if(pageSize===0) return 1;\n"
    "  return Math.max(1,Math.ceil(allDocs.length/pageSize));\n"
    "}\n"
    "\n"
    "function renderPage(p){\n"
    "  var tp=totalPages();\n"
    "  if(p<1) p=1; if(p>tp) p=tp;\n"
    "  currentPage=p;\n"
    "  var slice=pageSize===0?allDocs:allDocs.slice((p-1)*pageSize,(p-1)*pageSize+pageSize);\n"
    "  var tbody=document.querySelector('#target tbody');\n"
    "  tbody.innerHTML='';\n"
    "  slice.forEach(function(d){\n"
    "    var row=document.createElement('tr');\n"
    "    var cols=[d.created,d.added,d.title,d.corr,d.tags,d.type,d.path,d.val];\n"
    "    cols.forEach(function(v,i){\n"
    "      var td=document.createElement('td');\n"
    "      td.className='c'+i;\n"
    "      /* data-tooltip fuer JS-Tooltip-Engine */\n"
    "      if(v) td.setAttribute('data-tooltip', v);\n"
    "      if(i===2){\n"
    "        var a=document.createElement('a');\n"
    "        a.href=d.link||'#'; a.target='_blank'; a.rel='noopener noreferrer';\n"
    "        a.textContent=v||''; td.appendChild(a);\n"
    "      } else { td.textContent=v||''; }\n"
    "      var thEl=document.querySelector('th.c'+i);\n"
    "      if(thEl&&thEl.classList.contains('hidden')) td.classList.add('hidden');\n"
    "      row.appendChild(td);\n"
    "    });\n"
    "    tbody.appendChild(row);\n"
    "  });\n"
    "  var pagTop=document.getElementById('pag-top');\n"
    "  pagTop.classList.toggle('hidden',allDocs.length===0);\n"
    "  var pagBot=document.getElementById('pag-bot');\n"
    "  pagBot.classList.toggle('hidden',allDocs.length===0);\n"
    "  ['top','bot'].forEach(function(pos){\n"
    "    var info=document.getElementById('page-info-'+pos);\n"
    "    var tpl=T.page_info;\n"
    "    info.textContent=tpl.replace('{cur}',p).replace('{total}',tp).replace('{count}',allDocs.length);\n"
    "    var nav=document.getElementById('page-nav-'+pos);\n"
    "    nav.innerHTML='';\n"
    "    if(tp<=1) return;\n"
    "    var prev=document.createElement('button');\n"
    "    prev.className='page-btn'+(p===1?' disabled':'');\n"
    "    prev.textContent='\\u2039';\n"
    "    prev.onclick=function(){goToPage(p-1);};\n"
    "    nav.appendChild(prev);\n"
    "    buildPageNumbers(p,tp).forEach(function(x){\n"
    "      if(x==='...'){\n"
    "        var sp=document.createElement('span');\n"
    "        sp.className='page-ellipsis'; sp.textContent='\\u2026'; nav.appendChild(sp);\n"
    "      } else {\n"
    "        var btn=document.createElement('button');\n"
    "        btn.className='page-btn'+(x===p?' active':'');\n"
    "        btn.textContent=String(x);\n"
    "        (function(pg){btn.onclick=function(){goToPage(pg);};})(x);\n"
    "        nav.appendChild(btn);\n"
    "      }\n"
    "    });\n"
    "    var next=document.createElement('button');\n"
    "    next.className='page-btn'+(p===tp?' disabled':'');\n"
    "    next.textContent='\\u203A';\n"
    "    next.onclick=function(){goToPage(p+1);};\n"
    "    nav.appendChild(next);\n"
    "  });\n"
    "}\n"
    "\n"
    "function buildPageNumbers(cur,total){\n"
    "  var delta=2,pages=[],left=cur-delta,right=cur+delta,last=null;\n"
    "  for(var i=1;i<=total;i++){\n"
    "    if(i===1||i===total||(i>=left&&i<=right)){\n"
    "      if(last!==null&&i-last>1) pages.push('...');\n"
    "      pages.push(i); last=i;\n"
    "    }\n"
    "  }\n"
    "  return pages;\n"
    "}\n"
    "\n"
    "function buildMultiList(key){\n"
    "  var sel=document.getElementById('f_'+key);\n"
    "  var wrap=document.getElementById('wrap-'+key);\n"
    "  var items=[];\n"
    "  for(var i=0;i<sel.options.length;i++){\n"
    "    var opt=sel.options[i]; if(opt.value==='') continue;\n"
    "    items.push({value:opt.value,label:opt.textContent});\n"
    "  }\n"
    "  multiData[key]=items;\n"
    "  var div=document.createElement('div');\n"
    "  div.className='multi-list'; div.id='ml-'+key;\n"
    "  items.forEach(function(item){\n"
    "    var d=document.createElement('div');\n"
    "    d.className='multi-list-item';\n"
    "    d.setAttribute('data-value',item.value);\n"
    "    d.textContent=item.label;\n"
    "    if(multiSelected[key][item.value]) d.classList.add('selected');\n"
    "    d.addEventListener('click',function(){\n"
    "      var v=this.getAttribute('data-value');\n"
    "      if(multiSelected[key][v]){delete multiSelected[key][v];this.classList.remove('selected');}\n"
    "      else{multiSelected[key][v]=true;this.classList.add('selected');}\n"
    "    });\n"
    "    div.appendChild(d);\n"
    "  });\n"
    "  sel.style.display='none';\n"
    "  wrap.appendChild(div);\n"
    "}\n"
    "\n"
    "function destroyMultiList(key){\n"
    "  var sel=document.getElementById('f_'+key);\n"
    "  var wrap=document.getElementById('wrap-'+key);\n"
    "  var ml=document.getElementById('ml-'+key);\n"
    "  if(ml) wrap.removeChild(ml);\n"
    "  sel.style.display='';\n"
    "  var firstSel=Object.keys(multiSelected[key])[0]||'';\n"
    "  for(var i=0;i<sel.options.length;i++){\n"
    "    sel.options[i].selected=(sel.options[i].value===firstSel);\n"
    "  }\n"
    "}\n"
    "\n"
    "function toggleMode(key){\n"
    "  var btn=document.getElementById('toggle-'+key);\n"
    "  var hint=document.getElementById('hint-'+key);\n"
    "  var tr=T;\n"
    "  if(!multiMode[key]){\n"
    "    multiMode[key]=true;\n"
    "    var sel=document.getElementById('f_'+key);\n"
    "    var cur=sel.value;\n"
    "    if(cur&&cur!=='') multiSelected[key][cur]=true;\n"
    "    buildMultiList(key);\n"
    "    btn.textContent=tr.btn_single; btn.classList.add('multi-active');\n"
    "    hint.textContent=tr.multi_hint;\n"
    "  } else {\n"
    "    multiMode[key]=false;\n"
    "    destroyMultiList(key);\n"
    "    btn.textContent=tr.btn_multi; btn.classList.remove('multi-active');\n"
    "    hint.textContent='';\n"
    "  }\n"
    "  localStorage.setItem('paperless_multimode',JSON.stringify(multiMode));\n"
    "}\n"
    "window.toggleMode=toggleMode;\n"
    "\n"
    "function getSelected(key){\n"
    "  if(multiMode[key]) return Object.keys(multiSelected[key]);\n"
    "  var sel=document.getElementById('f_'+key);\n"
    "  if(!sel||!sel.value||sel.value==='') return [];\n"
    "  return [sel.value];\n"
    "}\n"
    "\n"
    "function resetFilters(){\n"
    "  document.getElementById('f_query').value='';\n"
    "  ['corr','type','tag','path'].forEach(function(k){\n"
    "    multiSelected[k]={};\n"
    "    if(multiMode[k]){\n"
    "      var ml=document.getElementById('ml-'+k);\n"
    "      if(ml) ml.querySelectorAll('.multi-list-item').forEach(function(item){item.classList.remove('selected');});\n"
    "    } else {\n"
    "      var sel=document.getElementById('f_'+k);\n"
    "      if(sel) sel.selectedIndex=0;\n"
    "    }\n"
    "  });\n"
    "  document.getElementById('f_date_gte').value='{{ default_date_from }}';\n"
    "  document.getElementById('f_date_lte').value='{{ default_date_to }}';\n"
    "}\n"
    "window.resetFilters=resetFilters;\n"
    "\n"
    "document.getElementById('token_eye').addEventListener('click',function(){\n"
    "  var inp=document.getElementById('cfg_token'),tr=T;\n"
    "  if(inp.type==='password'){inp.type='text';this.textContent=tr.token_hide;}\n"
    "  else{inp.type='password';this.textContent=tr.token_show;}\n"
    "});\n"
    "document.getElementById('btn-settings').addEventListener('click',function(){\n"
    "  document.getElementById('modal').style.display='flex';\n"
    "});\n"
    "document.getElementById('btn-cancel').addEventListener('click',function(){\n"
    "  document.getElementById('modal').style.display='none';\n"
    "});\n"
    "document.getElementById('btn-save').addEventListener('click',function(){\n"
    "  var url=document.getElementById('cfg_url').value.trim();\n"
    "  var token=document.getElementById('cfg_token').value.trim();\n"
    "  if(!url||!token){alert('Please enter URL and token.');return;}\n"
    "  fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,token:token})})\n"
    "  .then(function(r){return r.json();})\n"
    "  .then(function(d){if(d.status==='ok') location.reload(); else alert('Error: '+(d.msg||'Unknown'));})\n"
    "  .catch(function(e){alert('Connection error: '+e);});\n"
    "});\n"
    "\n"
    "function toggleCol(idx){\n"
    "  var th=document.querySelector('.c'+idx);\n"
    "  if(!th) return;\n"
    "  th.classList.toggle('hidden');\n"
    "  document.querySelectorAll('#target tbody tr').forEach(function(row){\n"
    "    if(row.cells[idx]) row.cells[idx].classList.toggle('hidden');\n"
    "  });\n"
    "}\n"
    "window.toggleCol=toggleCol;\n"
    "\n"
    "var currentSort={column:-1,direction:'asc'};\n"
    "function sortTable(n){\n"
    "  var headers=document.getElementById('target').querySelectorAll('thead th');\n"
    "  var dir=(currentSort.column===n&&currentSort.direction==='asc')?'desc':'asc';\n"
    "  var keys=['created','added','title','corr','tags','type','path','val'];\n"
    "  allDocs.sort(function(a,b){\n"
    "    var x=(a[keys[n]]||'').toLowerCase().trim();\n"
    "    var y=(b[keys[n]]||'').toLowerCase().trim();\n"
    "    var dx=Date.parse(x),dy=Date.parse(y);\n"
    "    if(!isNaN(dx)&&!isNaN(dy)) return dir==='asc'?dx-dy:dy-dx;\n"
    "    if(x<y) return dir==='asc'?-1:1;\n"
    "    if(x>y) return dir==='asc'?1:-1;\n"
    "    return 0;\n"
    "  });\n"
    "  headers.forEach(function(th){th.classList.remove('sorted-asc','sorted-desc');});\n"
    "  headers[n].classList.add(dir==='asc'?'sorted-asc':'sorted-desc');\n"
    "  currentSort={column:n,direction:dir};\n"
    "  renderPage(1);\n"
    "}\n"
    "window.sortTable=sortTable;\n"
    "\n"
    "async function loadDocs(){\n"
    "  var st=document.getElementById('status');\n"
    "  var wrap=document.getElementById('progress-bar-wrap');\n"
    "  var bar=document.getElementById('progress-bar');\n"
    "  var tr=T;\n"
    "  st.className=''; st.textContent=tr.st_loading;\n"
    "  wrap.style.display='block'; bar.style.width='0%';\n"
    "  allDocs=[]; currentPage=1;\n"
    "  var mode=document.getElementById('f_date_mode').value;\n"
    "  var query=document.getElementById('f_query').value.trim();\n"
    "  var gte=document.getElementById('f_date_gte').value;\n"
    "  var lte=document.getElementById('f_date_lte').value;\n"
    "  var corrVals=getSelected('corr');\n"
    "  var typeVals=getSelected('type');\n"
    "  var tagVals=getSelected('tag');\n"
    "  var pathVals=getSelected('path');\n"
    "  var baseParams=new URLSearchParams();\n"
    "  if(query) baseParams.append('query',query);\n"
    "  if(gte) baseParams.append(mode+'__date__gte',gte);\n"
    "  if(lte) baseParams.append(mode+'__date__lte',lte);\n"
    "  function buildParamSets(cV,tV,taV,pV,bp){\n"
    "    var corrs=cV.length?cV:[null];var types=tV.length?tV:[null];var paths=pV.length?pV:[null];\n"
    "    var sets=[];\n"
    "    corrs.forEach(function(c){types.forEach(function(t){paths.forEach(function(p){\n"
    "      var ps=new URLSearchParams(bp.toString());\n"
    "      if(c!==null){if(c==='__empty__') ps.append('correspondent__isnull','1'); else ps.append('correspondent__id',c);}\n"
    "      if(t!==null){if(t==='__empty__') ps.append('document_type__isnull','1'); else ps.append('document_type__id',t);}\n"
    "      if(p!==null){if(p==='__empty__') ps.append('storage_path__isnull','1'); else ps.append('storage_path__id',p);}\n"
    "      if(taV.length){\n"
    "        var hasEmpty=taV.indexOf('__empty__')!==-1;\n"
    "        var realTags=taV.filter(function(v){return v!=='__empty__';});\n"
    "        if(hasEmpty) ps.append('is_tagged','0');\n"
    "        realTags.forEach(function(tg){ps.append('tags__id__all',tg);});\n"
    "      }\n"
    "      sets.push(ps);\n"
    "    });});});\n"
    "    return sets;\n"
    "  }\n"
    "  var paramSets=buildParamSets(corrVals,typeVals,tagVals,pathVals,baseParams);\n"
    "  try{\n"
    "    var seenIds={}; var totalSets=paramSets.length;\n"
    "    for(var si=0;si<totalSets;si++){\n"
    "      var ps=paramSets[si];\n"
    "      var firstResp=await fetch('/api/data?'+ps.toString()+'&page=1');\n"
    "      if(!firstResp.ok) continue;\n"
    "      var firstData=await firstResp.json();\n"
    "      var total=firstData.count||0;\n"
    "      var apiPageSize=firstData.page_size||25;\n"
    "      var totalApiPages=Math.ceil(total/apiPageSize);\n"
    "      (firstData.results||[]).forEach(function(d){if(!seenIds[d.id]){seenIds[d.id]=true;allDocs.push(d);}});\n"
    "      for(var page=2;page<=totalApiPages;page++){\n"
    "        st.textContent=tr.st_page+' '+page+' '+tr.st_of+' '+totalApiPages+'...';\n"
    "        var resp=await fetch('/api/data?'+ps.toString()+'&page='+page);\n"
    "        if(!resp.ok) break;\n"
    "        var pd=await resp.json();\n"
    "        (pd.results||[]).forEach(function(d){if(!seenIds[d.id]){seenIds[d.id]=true;allDocs.push(d);}});\n"
    "      }\n"
    "      bar.style.width=Math.round(((si+1)/totalSets)*100)+'%';\n"
    "    }\n"
    "    st.textContent=allDocs.length+' '+tr.st_done;\n"
    "    renderPage(1);\n"
    "  } catch(e){\n"
    "    st.className='status-error'; st.textContent=T.st_error; console.error(e);\n"
    "  } finally {\n"
    "    setTimeout(function(){wrap.style.display='none';bar.style.width='0%';},800);\n"
    "  }\n"
    "}\n"
    "window.loadDocs=loadDocs;\n"
    "\n"
    "function exportCSV(){\n"
    "  if(!allDocs||allDocs.length===0){\n"
    "    alert('No documents to export. Please load documents first.');\n"
    "    return;\n"
    "  }\n"
    "  var tr=T;\n"
    "  var csv=tr.col.map(function(h){return '\"'+h+'\"';}).join(';')+'\\n';\n"
    "  allDocs.forEach(function(d){\n"
    "    var cols=[d.created,d.added,d.title,d.corr,d.tags,d.type,d.path,d.val];\n"
    "    csv+=cols.map(function(v){return '\"'+String(v==null?'':v).replace(/\"/g,'\"\"')+'\"';}).join(';')+'\\n';\n"
    "  });\n"
    "  var blob=new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8;'});\n"
    "  var url=URL.createObjectURL(blob);\n"
    "  var link=document.createElement('a');\n"
    "  link.href=url;\n"
    "  link.download=tr.csv_file;\n"
    "  document.body.appendChild(link);\n"
    "  link.click();\n"
    "  document.body.removeChild(link);\n"
    "  setTimeout(function(){URL.revokeObjectURL(url);},100);\n"
    "}\n"
    "window.exportCSV=exportCSV;\n"
    "\n"
    "var savedMode=localStorage.getItem('paperless_multimode');\n"
    "if(savedMode){\n"
    "  try{\n"
    "    var parsed=JSON.parse(savedMode);\n"
    "    ['corr','type','tag','path'].forEach(function(k){if(parsed[k]) toggleMode(k);});\n"
    "  }catch(e){}\n"
    "}\n"
    "if(!HAS_URL||!HAS_TOKEN) document.getElementById('modal').style.display='flex';\n"
    "\n"
    "})();\n"
    "</script>\n"
    "</body>\n"
    "</html>\n"
)


@app.route('/')
def index():
    conf = load_config()
    fetch_all_meta()
    default_from, default_to = get_default_dates()
    html = render_template_string(
        HTML_TEMPLATE,
        meta=meta_cache['data'],
        conf=conf,
        default_date_from=default_from,
        default_date_to=default_to
    )
    return Response(html, content_type='text/html; charset=utf-8')


@app.route('/api/settings', methods=['POST'])
@limiter.limit("10 per minute")
def settings():
    data = request.json
    if not data:
        return jsonify({"status": "error", "msg": "No data"}), 400
    url   = data.get('url', '').strip()
    token = data.get('token', '').strip()
    if not url or not token:
        return jsonify({"status": "error", "msg": "URL and token required"}), 400
    if not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({"status": "error", "msg": "Invalid URL scheme"}), 400
    save_config(url, token)
    meta_cache['last_fetch'] = 0
    return jsonify({"status": "ok"})


@app.route('/api/data')
@limiter.limit("60 per minute")
def get_data():
    conf = load_config()
    if not conf.get('url') or not conf.get('token'):
        return jsonify({"count": 0, "page_size": 25, "results": []})
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    ALLOWED_PARAMS = {
        'query',
        'correspondent__id', 'correspondent__isnull',
        'document_type__id', 'document_type__isnull',
        'storage_path__id',  'storage_path__isnull',
        'tags__id__all',     'is_tagged',
        'created__date__gte', 'created__date__lte',
        'added__date__gte',   'added__date__lte'
    }
    params = {}
    multi  = {}
    for k, v in request.args.to_dict(flat=False).items():
        if k in ALLOWED_PARAMS:
            clean = [x.strip() for x in v if x.strip()]
            if not clean: continue
            if len(clean)==1: params[k]=clean[0]
            else: multi[k]=clean
    params['page']      = page
    params['page_size'] = 25

    try:
        send_params = list(params.items())
        for k, vlist in multi.items():
            for v in vlist:
                send_params.append((k, v))
        r = requests.get(
            conf['url'] + "/api/documents/",
            headers=get_headers(),
            params=send_params,
            timeout=15
        )
        if r.status_code == 401:
            return jsonify({"error": "unauthorized", "count": 0, "results": []}), 401
        if r.status_code != 200:
            return jsonify({"error": "upstream_" + str(r.status_code), "count": 0, "results": []}), 502

        raw     = r.json()
        count   = raw.get('count', 0)
        results = raw.get('results', [])
        output  = []
        for d in results:
            doc_id = str(d.get('id', ''))
            output.append({
                "id":      doc_id,
                "created": (d.get('created','') or '').split('T')[0],
                "added":   (d.get('added',  '') or '').split('T')[0],
                "title":   d.get('title',''),
                "corr":    meta_cache['data']['correspondents'].get(d.get('correspondent'),""),
                "tags":    ", ".join(meta_cache['data']['tags'].get(tg,"") for tg in d.get('tags',[])),
                "type":    meta_cache['data']['document_types'].get(d.get('document_type'),""),
                "path":    meta_cache['data']['storage_paths'].get(d.get('storage_path'),""),
                "val":     doc_id,
                "link":    conf['url']+"/documents/"+doc_id if doc_id else ""
            })
        return jsonify({"count": count, "page_size": 25, "results": output})

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "connection_error", "count": 0, "results": []}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": "timeout", "count": 0, "results": []}), 504
    except Exception as e:
        print("Error: " + str(e))
        return jsonify({"error": "unknown", "count": 0, "results": []}), 500


@app.route('/api/meta/refresh', methods=['POST'])
@limiter.limit("5 per minute")
def refresh_meta():
    fetch_all_meta(force=True)
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=False)
