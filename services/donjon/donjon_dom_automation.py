from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

DONJON_FIELD_IDS = {
    'Dungeon Name': 'input-name', 'Dungeon Level': 'input-level', 'Party Size': 'input-n_pc',
    'Motif': 'input-motif', 'Random Seed': 'input-seed', 'Dungeon Size': 'input-dungeon_size',
    'Dungeon Layout': 'input-dungeon_layout', 'Peripheral Egress': 'input-peripheral_egress',
    'Room Layout': 'input-room_layout', 'Room Size': 'input-room_size', 'Polymorph Rooms': 'input-room_polymorph',
    'Doors': 'input-door_set', 'Corridors': 'input-corridor_layout', 'Remove Deadends': 'input-remove_deadends',
    'Stairs': 'input-add_stairs', 'Map Style': 'input-map_style', 'Grid': 'input-grid',
}

SET_CONTROL_BY_ID_JS = """(args) => { const id=String(args.id||''); const value=String(args.value||''); const el=document.getElementById(id); if(!el) return {ok:false, reason:'missing_id'}; function norm(s){return String(s||'').replace(/\\s+/g,' ').trim().toLowerCase();} if(el.tagName && el.tagName.toLowerCase()==='select'){ const wanted=norm(value); const opts=Array.from(el.options||[]); let m=opts.find(o=>norm(o.textContent)===wanted || norm(o.value)===wanted); if(!m) m=opts.find(o=>norm(o.textContent).includes(wanted) || norm(o.value).includes(wanted)); if(!m) return {ok:false, reason:'option_not_found', id:id, wanted:value, options:opts.map(o=>o.textContent)}; el.disabled=false; el.value=m.value; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return {ok:true, id:id, value:el.value, text:m.textContent}; } el.value=value; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); return {ok:true, id:id, value:el.value}; }"""
CLICK_CONSTRUCT_JS = """() => { function visible(el){return !!(el && (el.offsetParent!==null || el.getClientRects().length));} function txt(el){return String(el.value||el.textContent||'').replace(/\\s+/g,' ').trim().toLowerCase();} const c=Array.from(document.querySelectorAll('input[type=submit],input[type=button],button,a')).filter(visible).filter(el=>/construct dungeon|construct/.test(txt(el))); const p=c.find(el=>/construct dungeon/.test(txt(el)))||c[0]; if(!p) return false; p.scrollIntoView({block:'center',inline:'center'}); p.click(); return true; }"""
CLICK_BUTTON_BY_TEXT_JS = """(wanted) => { function visible(el){return !!(el && (el.offsetParent!==null || el.getClientRects().length));} function txt(el){return String(el.value||el.textContent||'').replace(/\\s+/g,' ').trim().toLowerCase();} const needle=String(wanted||'').trim().toLowerCase(); const c=Array.from(document.querySelectorAll('input[type=submit],input[type=button],button,a')).filter(visible).filter(el=>txt(el)===needle || txt(el).includes(needle)); const p=c[0]; if(!p) return false; p.scrollIntoView({block:'center',inline:'center'}); p.click(); return true; }"""
READY_STATE_JS = """() => { const body=String(document.body ? document.body.innerText : ''); const lower=body.toLowerCase(); const hasRoom=/room #\\d+/.test(body); const hasBack=lower.includes('back to settings'); const hasDownload=lower.includes('download'); const hasMap=!!document.querySelector('#dungeon_map img, map#dungeon_areas area, area[href^="#room_"]'); const constructingVisible=lower.includes('constructing dungeon') && !hasRoom && !hasBack && !hasMap; return {ready:!!((hasRoom||hasBack||hasDownload||hasMap)&&!constructingVisible),hasRoom,hasBack,hasDownload,hasMap,constructingVisible,textLength:body.length}; }"""
EXPAND_DOWNLOAD_PANEL_JS = """() => { function visible(el){return !!(el && (el.offsetParent!==null || el.getClientRects().length));} function txt(el){return String(el.value||el.textContent||'').replace(/\\s+/g,' ').trim().toLowerCase();} const d=Array.from(document.querySelectorAll('input[type=button],button,a')).filter(visible).find(el=>txt(el)==='download' || txt(el).startsWith('download')); if(d){d.scrollIntoView({block:'center',inline:'center'}); d.click(); return true;} return false; }"""
VUE_DOWNLOAD_JS = """(kind) => { const root=document.querySelector('#dungeon_app'); const app=root && (root.__vue__ || (root.__vue_app__ && root.__vue_app__._instance && root.__vue_app__._instance.proxy)); if(!app) return {ok:false, reason:'vue_not_found'}; if(typeof app.download_file !== 'function') return {ok:false, reason:'download_file_missing', keys:Object.keys(app).slice(0,50)}; app.download_file(kind); return {ok:true, kind:kind}; }"""

class DonjonDomAutomation:
    @staticmethod
    def set_control_by_id(page: Any, control_id: str, value: str) -> Dict[str, Any]:
        return page.evaluate(SET_CONTROL_BY_ID_JS, {'id': control_id, 'value': value})
    @staticmethod
    def set_by_label(page: Any, label: str, value: str) -> bool:
        cid = DONJON_FIELD_IDS.get(label)
        return bool(cid and DonjonDomAutomation.set_control_by_id(page, cid, value).get('ok'))
    @staticmethod
    def apply_form_settings(page: Any, settings: Dict[str, str]) -> List[str]:
        warnings=[]
        for label in ['Dungeon Layout','Dungeon Size','Peripheral Egress','Room Layout','Room Size','Polymorph Rooms','Doors','Corridors','Remove Deadends','Stairs','Map Style','Grid','Motif','Party Size']:
            if label in settings:
                ok=DonjonDomAutomation.set_by_label(page,label,settings[label]); page.wait_for_timeout(150)
                if not ok: warnings.append(f'Could not set Donjon field: {label}={settings[label]}')
        return warnings
    @staticmethod
    def click_construct_or_generate(page: Any) -> bool: return bool(page.evaluate(CLICK_CONSTRUCT_JS))
    @staticmethod
    def ready_state(page: Any) -> Dict[str, Any]:
        try: return dict(page.evaluate(READY_STATE_JS))
        except Exception as exc: return {'ready':False,'error':repr(exc)}
    @staticmethod
    def wait_for_result_ready(page: Any, timeout_ms: int = 180000, settle_ms: int = 3000) -> Dict[str, Any]:
        try:
            page.wait_for_function("""() => { const body=String(document.body ? document.body.innerText : ''); const lower=body.toLowerCase(); return /room #\\d+/.test(body) || lower.includes('back to settings') || !!document.querySelector('#dungeon_map img, map#dungeon_areas area, area[href^="#room_"]'); }""", timeout=timeout_ms)
        except Exception: pass
        page.wait_for_timeout(settle_ms)
        state=DonjonDomAutomation.ready_state(page)
        if not state.get('ready'):
            page.wait_for_timeout(5000); state=DonjonDomAutomation.ready_state(page)
        return state
    @staticmethod
    def expand_download_panel(page: Any) -> bool:
        return bool(page.evaluate(EXPAND_DOWNLOAD_PANEL_JS))
    @staticmethod
    def click_button_by_text(page: Any, text: str) -> bool:
        return bool(page.evaluate(CLICK_BUTTON_BY_TEXT_JS, text))
    @staticmethod
    def click_back_to_settings(page: Any) -> bool:
        return DonjonDomAutomation.click_button_by_text(page, 'Back to Settings')
    @staticmethod
    def _download_with_click(page: Any, button_text: str, target_dir: str | Path, file_stem: str, timeout_ms: int) -> Optional[str]:
        target_root=Path(target_dir); target_root.mkdir(parents=True, exist_ok=True)
        try:
            with page.expect_download(timeout=timeout_ms) as download_info:
                if not DonjonDomAutomation.click_button_by_text(page, button_text): return None
            dl=download_info.value; target=target_root/(dl.suggested_filename or f'{file_stem}_{button_text.lower().replace(" ","_")}')
            dl.save_as(str(target)); return str(target)
        except Exception: return None
    @staticmethod
    def _download_with_vue(page: Any, kind: str, target_dir: str | Path, file_stem: str, timeout_ms: int) -> Optional[str]:
        target_root=Path(target_dir); target_root.mkdir(parents=True, exist_ok=True)
        try:
            with page.expect_download(timeout=timeout_ms) as download_info:
                res=page.evaluate(VUE_DOWNLOAD_JS, kind)
                if not res or not res.get('ok'): return None
            dl=download_info.value; target=target_root/(dl.suggested_filename or f'{file_stem}_{kind}')
            dl.save_as(str(target)); return str(target)
        except Exception: return None
    @staticmethod
    def download_available_exports(page: Any, target_dir: str | Path, file_stem: str, timeout_ms: int = 30000) -> Dict[str, str]:
        outputs={}
        # Prefer Vue direct method because buttons are generated under v-if and can be invisible in static source.
        for kind,key in [('json','json'),('pdf','pdf'),('html','html_page'),('image','map'),('player','players_map'),('tsv','tsv')]:
            path=DonjonDomAutomation._download_with_vue(page, kind, target_dir, file_stem, timeout_ms)
            if path: outputs[key]=path
        # Fallback to visible menu buttons.
        if len(outputs) < 2:
            DonjonDomAutomation.expand_download_panel(page); page.wait_for_timeout(1000)
            for label,key in [('JSON','json'),('PDF','pdf'),('HTML Page','html_page'),('Download Map','map'),("Player's Map",'players_map'),('TSV','tsv')]:
                if key not in outputs:
                    path=DonjonDomAutomation._download_with_click(page,label,target_dir,file_stem,timeout_ms)
                    if path: outputs[key]=path
        return outputs
