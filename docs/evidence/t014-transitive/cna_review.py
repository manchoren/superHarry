import concurrent.futures,datetime,hashlib,json,pathlib,urllib.request
p=pathlib.Path('docs/evidence/t014-transitive/catalog-review.json'); packages=json.loads(p.read_text(encoding='utf-8'))['packages']; remaining={}
for item in packages:
 name=item['name']; short=name.split('x86_64-')[-1]
 if short.startswith('qemu') or short in ('gnutls','libssh2'):continue
 for cve in item['catalog_cves']:remaining.setdefault(cve,[]).append({'name':name,'version':item['snapshot_version']})
def query(entry):
 cve,pkgs=entry; rec={'id':cve,'packages':pkgs,'source':'https://cveawg.mitre.org/api/cve/'+cve}
 try:
  with urllib.request.urlopen(rec['source'],timeout=25) as f:raw=f.read()
  data=json.loads(raw); cna=data.get('containers',{}).get('cna',{}); rec['retrieval']='ok';rec['record_sha256']=hashlib.sha256(raw).hexdigest();rec['state']=data.get('cveMetadata',{}).get('state');rec['descriptions']=[x.get('value','') for x in cna.get('descriptions',[]) if x.get('lang')=='en'];rec['affected']=cna.get('affected',[]);rec['references']=[x.get('url','') for x in cna.get('references',[])];rec['date_updated']=data.get('cveMetadata',{}).get('dateUpdated')
 except Exception as e:rec['retrieval']='error';rec['error']=type(e).__name__+': '+str(e)
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:r=sorted(executor.map(query,remaining.items()),key=lambda x:x['id'])
out={'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'catalog_review_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'CNA records for catalog CVEs excluding QEMU, GnuTLS and libssh2; not a completed vulnerability disposition','records':r}
pathlib.Path('docs/evidence/t014-transitive/cna-records.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('records',len(r),'ok',sum(x['retrieval']=='ok' for x in r),'error',sum(x['retrieval']!='ok' for x in r))
