from __future__ import annotations
import os,time,uuid
from datetime import datetime,timezone
from typing import Any
import pandas as pd
import requests
from crypto_platform.platform import load_all,connect
from crypto_platform.module2 import MODULE2_SCHEMA
from crypto_platform.module3 import MODULE3_SCHEMA
from crypto_platform.module5 import MODULE5_SCHEMA
from crypto_platform.module6 import MODULE6_SCHEMA
from crypto_platform.module7 import MODULE7_SCHEMA
from crypto_platform.module8 import MODULE8_SCHEMA
from crypto_platform.module9 import MODULE9_SCHEMA
from crypto_platform.module10 import MODULE10_SCHEMA
from crypto_platform.module11 import MODULE11_SCHEMA

MODULE12_SCHEMA=r"""
CREATE TABLE IF NOT EXISTS module12_runs(run_id VARCHAR PRIMARY KEY,started_at_utc TIMESTAMPTZ,completed_at_utc TIMESTAMPTZ,status VARCHAR,mappings_verified INTEGER,mappings_rejected INTEGER,invalid_rows_removed INTEGER,history_rows_repaired INTEGER,derivatives_rows INTEGER,universe_rows_removed INTEGER,notes VARCHAR,platform_version VARCHAR);
CREATE TABLE IF NOT EXISTS exchange_metadata_assets(provider VARCHAR,provider_asset_code VARCHAR,normalized_symbol VARCHAR,display_name VARCHAR,metadata_json VARCHAR,collected_at_utc TIMESTAMPTZ,PRIMARY KEY(provider,provider_asset_code));
CREATE TABLE IF NOT EXISTS exchange_metadata_markets(provider VARCHAR,provider_symbol VARCHAR,base_asset_code VARCHAR,normalized_base_symbol VARCHAR,quote_asset_code VARCHAR,normalized_quote_symbol VARCHAR,market_type VARCHAR,active BOOLEAN,metadata_json VARCHAR,collected_at_utc TIMESTAMPTZ,PRIMARY KEY(provider,provider_symbol,market_type));
CREATE TABLE IF NOT EXISTS symbol_mapping_audit(run_id VARCHAR,asset_id VARCHAR,research_symbol VARCHAR,provider VARCHAR,provider_symbol VARCHAR,market_type VARCHAR,expected_base_symbol VARCHAR,actual_base_symbol VARCHAR,expected_quote_symbols VARCHAR,actual_quote_symbol VARCHAR,exact_match BOOLEAN,accepted BOOLEAN,rejection_reason VARCHAR,audited_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,asset_id,provider,provider_symbol,market_type));
CREATE TABLE IF NOT EXISTS history_integrity_audit(run_id VARCHAR,asset_id VARCHAR,source VARCHAR,invalid_epoch_rows INTEGER,invalid_future_rows INTEGER,duplicate_rows INTEGER,rows_removed INTEGER,first_valid_date DATE,latest_valid_date DATE,audited_at_utc TIMESTAMPTZ,PRIMARY KEY(run_id,asset_id,source));
CREATE TABLE IF NOT EXISTS data_integrity_summary(asset_id VARCHAR PRIMARY KEY,active_in_universe BOOLEAN,verified_spot_providers INTEGER,verified_perpetual_providers INTEGER,history_days INTEGER,history_coverage_pct DOUBLE,invalid_rows_removed INTEGER,derivatives_supported BOOLEAN,integrity_status VARCHAR,calculated_at_utc TIMESTAMPTZ);
CREATE OR REPLACE VIEW latest_mapping_audit AS SELECT a.* FROM symbol_mapping_audit a JOIN (SELECT run_id FROM module12_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
CREATE OR REPLACE VIEW latest_history_integrity_audit AS SELECT a.* FROM history_integrity_audit a JOIN (SELECT run_id FROM module12_runs ORDER BY started_at_utc DESC LIMIT 1) r USING(run_id);
CREATE OR REPLACE VIEW latest_data_integrity_summary AS SELECT * FROM data_integrity_summary ORDER BY integrity_status,asset_id;
"""
ALIASES={'BTC':{'BTC','XBT'},'XBT':{'BTC','XBT'},'DOGE':{'DOGE','XDG'},'XDG':{'DOGE','XDG'}}
def utcnow(): return datetime.now(timezone.utc)
def normalize_symbol(v):
    t=str(v or '').upper()
    for x in ['.S','.M','-','_','/',' ']: t=t.replace(x,'')
    if t.startswith('X') and t[1:] in {'XBT','ETH','XRP','LTC','ETC','XMR'}: t=t[1:]
    if t.startswith('Z') and t[1:] in {'USD','EUR','GBP','JPY'}: t=t[1:]
    return t
def symbol_equivalent(a,b):
    a,b=normalize_symbol(a),normalize_symbol(b)
    return bool(ALIASES.get(a,{a}) & ALIASES.get(b,{b}))

class Module12Runner:
    def __init__(self):
        self.settings,self.core_assets=load_all(); self.conn=connect(self.settings)
        for schema in [MODULE2_SCHEMA,MODULE3_SCHEMA,MODULE5_SCHEMA,MODULE6_SCHEMA,MODULE7_SCHEMA,MODULE8_SCHEMA,MODULE9_SCHEMA,MODULE10_SCHEMA,MODULE11_SCHEMA,MODULE12_SCHEMA]: self.conn.execute(schema)
        self.config=self.settings['module12']; self.run_id=str(uuid.uuid4()); self.started=utcnow(); self.session=requests.Session(); self.session.headers.update({'User-Agent':'CryptoIntelligencePlatform/4.0'})
        key=os.getenv('COINGECKO_API_KEY','').strip()
        if key: self.session.headers['x-cg-demo-api-key']=key
    def upsert(self,table,frame):
        if frame.empty:return
        self.conn.register('_stage',frame); cols=','.join(frame.columns); self.conn.execute(f'INSERT OR REPLACE INTO {table}({cols}) SELECT {cols} FROM _stage'); self.conn.unregister('_stage')
    def get_json(self,url,params=None,retries=3):
        err=None
        for i in range(retries):
            try:
                r=self.session.get(url,params=params,timeout=40); r.raise_for_status(); return r.json()
            except Exception as e:
                err=e
                if i+1<retries: time.sleep(2**i)
        raise RuntimeError(f'{url}: {err}')
    def collect_exchange_metadata(self):
        now=utcnow(); markets=[]; assets=[]
        try:
            for m in self.get_json('https://api.binance.com/api/v3/exchangeInfo').get('symbols',[]):
                markets.append({'provider':'binance','provider_symbol':m['symbol'],'base_asset_code':m['baseAsset'],'normalized_base_symbol':normalize_symbol(m['baseAsset']),'quote_asset_code':m['quoteAsset'],'normalized_quote_symbol':normalize_symbol(m['quoteAsset']),'market_type':'spot','active':m.get('status')=='TRADING','metadata_json':str(m),'collected_at_utc':now})
        except Exception: pass
        try:
            for m in self.get_json('https://fapi.binance.com/fapi/v1/exchangeInfo').get('symbols',[]):
                c=m.get('contractType'); markets.append({'provider':'binance','provider_symbol':m['symbol'],'base_asset_code':m['baseAsset'],'normalized_base_symbol':normalize_symbol(m['baseAsset']),'quote_asset_code':m['quoteAsset'],'normalized_quote_symbol':normalize_symbol(m['quoteAsset']),'market_type':'perpetual' if c=='PERPETUAL' else 'futures','active':m.get('status')=='TRADING' and c=='PERPETUAL','metadata_json':str(m),'collected_at_utc':now})
        except Exception: pass
        try:
            for m in self.get_json('https://api.exchange.coinbase.com/products'):
                markets.append({'provider':'coinbase','provider_symbol':m['id'],'base_asset_code':m['base_currency'],'normalized_base_symbol':normalize_symbol(m['base_currency']),'quote_asset_code':m['quote_currency'],'normalized_quote_symbol':normalize_symbol(m['quote_currency']),'market_type':'spot','active':m.get('status')=='online','metadata_json':str(m),'collected_at_utc':now})
        except Exception: pass
        ka={}
        try:
            for code,meta in self.get_json('https://api.kraken.com/0/public/Assets').get('result',{}).items():
                alt=normalize_symbol(meta.get('altname',code)); ka[code]=alt; assets.append({'provider':'kraken','provider_asset_code':code,'normalized_symbol':alt,'display_name':meta.get('altname',code),'metadata_json':str(meta),'collected_at_utc':now})
        except Exception: pass
        try:
            for sym,m in self.get_json('https://api.kraken.com/0/public/AssetPairs').get('result',{}).items():
                bc,qc=m.get('base'),m.get('quote'); markets.append({'provider':'kraken','provider_symbol':sym,'base_asset_code':bc,'normalized_base_symbol':ka.get(bc,normalize_symbol(bc)),'quote_asset_code':qc,'normalized_quote_symbol':ka.get(qc,normalize_symbol(qc)),'market_type':'spot','active':True,'metadata_json':str(m),'collected_at_utc':now})
        except Exception: pass
        mf=pd.DataFrame(markets); self.upsert('exchange_metadata_markets',mf); self.upsert('exchange_metadata_assets',pd.DataFrame(assets)); return mf
    def remove_excluded(self):
        ids=set(self.config['exclusions']['remove_asset_ids']); syms={str(x).upper() for x in self.config['exclusions']['remove_symbols']}; u=self.conn.execute("SELECT asset_id,symbol FROM research_universe WHERE inclusion_status='INCLUDED'").fetchdf(); remove=set(u[u.asset_id.isin(ids)|u.symbol.str.upper().isin(syms)].asset_id)
        if remove:
            marks=','.join(['?']*len(remove)); self.conn.execute(f"UPDATE research_universe SET inclusion_status='EXCLUDED',inclusion_reason='Removed by v3.2 integrity exclusions.' WHERE asset_id IN ({marks})",list(remove))
        return len(remove)
    def audit_and_rebuild(self,u,meta):
        now=utcnow(); quotes=[normalize_symbol(x) for x in self.config['mapping']['quote_priority']]; audits=[]; accepted=[]
        for _,a in u.iterrows():
            exp=normalize_symbol(a.symbol)
            for provider in ['binance','coinbase','kraken']:
                for mt in ['spot','perpetual']:
                    c=meta[(meta.provider==provider)&(meta.market_type==mt)&meta.active.fillna(False)].copy()
                    if c.empty: continue
                    c=c[c.normalized_base_symbol.apply(lambda x:symbol_equivalent(exp,x)) & c.normalized_quote_symbol.isin(quotes)]
                    if c.empty: continue
                    c['qr']=c.normalized_quote_symbol.apply(quotes.index); row=c.sort_values(['qr','provider_symbol']).iloc[0]; exact=symbol_equivalent(exp,row.normalized_base_symbol)
                    audits.append({'run_id':self.run_id,'asset_id':a.asset_id,'research_symbol':a.symbol,'provider':provider,'provider_symbol':row.provider_symbol,'market_type':mt,'expected_base_symbol':exp,'actual_base_symbol':row.normalized_base_symbol,'expected_quote_symbols':','.join(quotes),'actual_quote_symbol':row.normalized_quote_symbol,'exact_match':exact,'accepted':exact,'rejection_reason':None if exact else 'Base symbol mismatch.','audited_at_utc':now})
                    if exact: accepted.append({'asset_id':a.asset_id,'provider':provider,'provider_symbol':row.provider_symbol,'quote_currency':row.normalized_quote_symbol,'market_type':mt,'mapping_method':'exact_exchange_metadata_v3_2','mapping_confidence':1.0,'active':True,'last_verified_utc':now})
        self.conn.execute('UPDATE exchange_symbol_map SET active=FALSE'); af=pd.DataFrame(accepted); self.upsert('exchange_symbol_map',af); self.upsert('symbol_mapping_audit',pd.DataFrame(audits)); return len(af),sum(1 for x in audits if not x['accepted'])
    def clean_history(self):
        min_date=pd.Timestamp(self.config['integrity']['minimum_valid_date']); max_date=(pd.Timestamp.now().normalize()+pd.Timedelta(days=int(self.config['integrity']['maximum_future_days'])))
        h=self.conn.execute('SELECT asset_id,source,observation_date,COUNT(*) row_count FROM research_market_daily GROUP BY asset_id,source,observation_date').fetchdf()
        if h.empty:return 0
        h.observation_date=pd.to_datetime(h.observation_date); audits=[]; total=0
        for (aid,src),g in h.groupby(['asset_id','source']):
            epoch=int((g.observation_date<min_date).sum()); future=int((g.observation_date>max_date).sum()); dup=int((g.row_count-1).clip(lower=0).sum()); removed=epoch+future+dup; valid=g[(g.observation_date>=min_date)&(g.observation_date<=max_date)]; total+=removed
            audits.append({'run_id':self.run_id,'asset_id':aid,'source':src,'invalid_epoch_rows':epoch,'invalid_future_rows':future,'duplicate_rows':dup,'rows_removed':removed,'first_valid_date':valid.observation_date.min().date() if not valid.empty else None,'latest_valid_date':valid.observation_date.max().date() if not valid.empty else None,'audited_at_utc':utcnow()})
        self.conn.execute('DELETE FROM research_market_daily WHERE observation_date<? OR observation_date>?',[min_date.date(),max_date.date()]); self.upsert('history_integrity_audit',pd.DataFrame(audits)); return total
    def history_count(self,aid): return int(self.conn.execute('SELECT COUNT(DISTINCT observation_date) FROM research_market_daily WHERE asset_id=? AND observation_date>=?',[aid,self.config['integrity']['minimum_valid_date']]).fetchone()[0])
    def fetch_coinbase(self,aid,sym,start,end):
        rows=[]; cur=start
        while cur<=end:
            stop=min(cur+pd.Timedelta(days=299),end); data=self.get_json(f'https://api.exchange.coinbase.com/products/{sym}/candles',{'granularity':86400,'start':cur.isoformat(),'end':stop.isoformat()},2)
            for c in data:
                d=pd.to_datetime(int(c[0]),unit='s',utc=True)
                if d.year>=2013: rows.append({'asset_id':aid,'observation_date':d.date(),'price_usd':float(c[4]),'market_cap_usd':None,'volume_24h_usd':float(c[5])*float(c[4]),'source':'coinbase','source_symbol':sym,'collected_at_utc':utcnow()})
            cur=stop+pd.Timedelta(days=1)
        return pd.DataFrame(rows)
    def fetch_kraken(self,aid,sym,start,end):
        data=self.get_json('https://api.kraken.com/0/public/OHLC',{'pair':sym,'interval':1440,'since':int(start.timestamp())},2).get('result',{}); key=next((k for k in data if k!='last'),None); rows=[]
        if key:
            for c in data[key]:
                d=pd.to_datetime(int(c[0]),unit='s',utc=True)
                if d.year>=2013 and d<=end: rows.append({'asset_id':aid,'observation_date':d.date(),'price_usd':float(c[4]),'market_cap_usd':None,'volume_24h_usd':float(c[6])*float(c[4]),'source':'kraken','source_symbol':sym,'collected_at_utc':utcnow()})
        return pd.DataFrame(rows)
    def fetch_binance(self,aid,sym,start,end):
        rows=[]; cur=int(start.timestamp()*1000); endms=int(end.timestamp()*1000)
        while cur<=endms:
            data=self.get_json('https://api.binance.com/api/v3/klines',{'symbol':sym,'interval':'1d','startTime':cur,'endTime':endms,'limit':1000},2)
            if not data: break
            for c in data:
                d=pd.to_datetime(int(c[0]),unit='ms',utc=True)
                if d.year>=2013: rows.append({'asset_id':aid,'observation_date':d.date(),'price_usd':float(c[4]),'market_cap_usd':None,'volume_24h_usd':float(c[7]),'source':'binance','source_symbol':sym,'collected_at_utc':utcnow()})
            nxt=int(data[-1][0])+86400000
            if nxt<=cur or len(data)<1000: break
            cur=nxt
        return pd.DataFrame(rows)
    def fetch_coingecko(self,aid,days):
        data=self.get_json(f'https://api.coingecko.com/api/v3/coins/{aid}/market_chart',{'vs_currency':'usd','days':days,'interval':'daily'},2); caps={int(t):v for t,v in data.get('market_caps',[])}; vols={int(t):v for t,v in data.get('total_volumes',[])}; rows=[]
        for t,p in data.get('prices',[]):
            d=pd.to_datetime(int(t),unit='ms',utc=True)
            if d.year>=2013: rows.append({'asset_id':aid,'observation_date':d.date(),'price_usd':float(p),'market_cap_usd':float(caps[int(t)]) if int(t) in caps else None,'volume_24h_usd':float(vols[int(t)]) if int(t) in vols else None,'source':'coingecko_history','source_symbol':aid,'collected_at_utc':utcnow()})
        return pd.DataFrame(rows)
    def repair_history(self,u):
        cfg=self.config['history_repair']; end=pd.Timestamp.now(tz='UTC').normalize(); start=end-pd.Timedelta(days=int(cfg['target_days'])); maps=self.conn.execute('SELECT * FROM latest_symbol_map').fetchdf(); frames=[]
        for _,a in u.head(int(cfg['max_assets_per_run'])).iterrows():
            if self.history_count(a.asset_id)>=int(cfg['minimum_acceptable_days']): continue
            for provider in cfg['provider_priority']:
                try:
                    if provider=='coingecko': f=self.fetch_coingecko(a.asset_id,int(cfg['coingecko_fallback_days']))
                    else:
                        m=maps[(maps.asset_id==a.asset_id)&(maps.provider==provider)&(maps.market_type=='spot')]
                        if m.empty: continue
                        sym=m.iloc[0].provider_symbol
                        f=self.fetch_binance(a.asset_id,sym,start,end) if provider=='binance' else self.fetch_coinbase(a.asset_id,sym,start,end) if provider=='coinbase' else self.fetch_kraken(a.asset_id,sym,start,end)
                except Exception: f=pd.DataFrame()
                if not f.empty: frames.append(f); break
        combined=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(); self.upsert('research_market_daily',combined); return len(combined)
    def collect_derivatives(self):
        maps=self.conn.execute("SELECT * FROM latest_symbol_map WHERE provider='binance' AND market_type='perpetual'").fetchdf(); now=utcnow(); fr=[]; oi=[]; status=[]
        for _,m in maps.iterrows():
            fc=oc=0; err=None
            try:
                data=self.get_json('https://fapi.binance.com/fapi/v1/fundingRate',{'symbol':m.provider_symbol,'limit':int(self.config['derivatives']['funding_limit'])},2)
                if data:
                    f=pd.DataFrame(data); f['fundingTime']=pd.to_datetime(f.fundingTime.astype('int64'),unit='ms',utc=True); f['fundingRate']=pd.to_numeric(f.fundingRate,errors='coerce')
                    for d,g in f.groupby(f.fundingTime.dt.date): fr.append({'asset_id':m.asset_id,'symbol':m.provider_symbol,'observation_date':d,'average_funding_rate':float(g.fundingRate.mean()),'minimum_funding_rate':float(g.fundingRate.min()),'maximum_funding_rate':float(g.fundingRate.max()),'funding_observations':len(g),'source':'binance_futures','collected_at_utc':now}); fc+=1
                x=self.get_json('https://fapi.binance.com/fapi/v1/openInterest',{'symbol':m.provider_symbol},2); oi.append({'asset_id':m.asset_id,'symbol':m.provider_symbol,'observation_time_utc':now,'open_interest_contracts':float(x['openInterest']),'source':'binance_futures','collected_at_utc':now}); oc=1
            except Exception as e: err=str(e)[:500]
            status.append({'asset_id':m.asset_id,'provider':'binance','provider_symbol':m.provider_symbol,'supported':fc>0 or oc>0,'funding_rows':fc,'open_interest_rows':oc,'status':'ONLINE' if fc>0 or oc>0 else 'FAILED','error_message':err,'checked_at_utc':now})
        self.upsert('derivatives_funding_daily',pd.DataFrame(fr)); self.upsert('derivatives_open_interest',pd.DataFrame(oi)); self.upsert('derivatives_collection_status',pd.DataFrame(status)); return len(fr)+len(oi)
    def summary(self,u):
        target=int(self.config['history_repair']['target_days']); maps=self.conn.execute('SELECT * FROM latest_symbol_map').fetchdf(); aud=self.conn.execute('SELECT asset_id,SUM(rows_removed) removed FROM latest_history_integrity_audit GROUP BY asset_id').fetchdf(); der=self.conn.execute('SELECT asset_id,MAX(CAST(supported AS INTEGER)) supported FROM derivatives_collection_status GROUP BY asset_id').fetchdf(); rows=[]
        for _,a in u.iterrows():
            h=self.history_count(a.asset_id); sp=maps[(maps.asset_id==a.asset_id)&(maps.market_type=='spot')].provider.nunique(); pp=maps[(maps.asset_id==a.asset_id)&(maps.market_type=='perpetual')].provider.nunique(); rv=aud[aud.asset_id==a.asset_id].removed; rem=int(rv.iloc[0]) if not rv.empty and pd.notna(rv.iloc[0]) else 0; dv=der[der.asset_id==a.asset_id].supported; ds=bool(dv.iloc[0]) if not dv.empty else False; cov=min(100,h/target*100); status='UNRESOLVED' if sp==0 and h<30 else 'LIMITED_HISTORY' if h<int(self.config['history_repair']['minimum_acceptable_days']) else 'CLEANED' if rem>0 else 'GOOD' if cov>=60 else 'PARTIAL'; rows.append({'asset_id':a.asset_id,'active_in_universe':True,'verified_spot_providers':sp,'verified_perpetual_providers':pp,'history_days':h,'history_coverage_pct':cov,'invalid_rows_removed':rem,'derivatives_supported':ds,'integrity_status':status,'calculated_at_utc':utcnow()})
        f=pd.DataFrame(rows); self.upsert('data_integrity_summary',f); return len(f)
    def run(self):
        self.conn.execute("UPDATE module12_runs SET status='FAILED',completed_at_utc=? WHERE status='RUNNING'",[utcnow()]); self.conn.execute("INSERT INTO module12_runs VALUES (?,?,NULL,'RUNNING',0,0,0,0,0,0,NULL,'4.0.0')",[self.run_id,self.started]); removed=self.remove_excluded(); u=self.conn.execute('SELECT * FROM latest_research_universe').fetchdf()
        if u.empty: raise RuntimeError('No active research universe. Run Module 10 first.')
        meta=self.collect_exchange_metadata(); verified,rejected=self.audit_and_rebuild(u,meta); invalid=self.clean_history(); repaired=self.repair_history(u); derivatives=self.collect_derivatives(); count=self.summary(u); notes=f'metadata={len(meta)}; verified={verified}; rejected={rejected}; invalid={invalid}; repaired={repaired}; derivatives={derivatives}; removed={removed}; summary={count}.'; self.conn.execute("UPDATE module12_runs SET completed_at_utc=?,status='SUCCESS',mappings_verified=?,mappings_rejected=?,invalid_rows_removed=?,history_rows_repaired=?,derivatives_rows=?,universe_rows_removed=?,notes=? WHERE run_id=?",[utcnow(),verified,rejected,invalid,repaired,derivatives,removed,notes,self.run_id]); self.conn.close(); return {'run_id':self.run_id,'status':'SUCCESS','mappings_verified':verified,'mappings_rejected':rejected,'invalid_rows_removed':invalid,'history_rows_repaired':repaired,'derivatives_rows':derivatives,'universe_rows_removed':removed,'summary_rows':count}
def run_module12(): return Module12Runner().run()
