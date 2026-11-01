import concurrent.futures, datetime, hashlib, html, json, re, urllib.request
from pathlib import Path
source=Path('docs/evidence/t014-msys2/qemu-inventory.json')
packages=json.loads(source.read_text(encoding='utf-8'))['packages']
def scan(pkg):
    name=pkg['name']; url='https://packages.msys2.org/packages/'+name
    result={'name':name,'snapshot_version':pkg['version'],'snapshot_sha256':pkg['sha256_declared'],'url':url}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'superHarry-T014-review/1.0'})
        with urllib.request.urlopen(req,timeout=30) as f: data=f.read(); result['http_status']=f.status
        text=data.decode('utf-8'); result['page_sha256']=hashlib.sha256(data).hexdigest()
        version=re.search(r'Version:</dt>\s*<dd[^>]*>([^<]+)</dd>',text)
        sha=re.search(r'SHA256:</dt>\s*<dd[^>]*>\s*<code>([0-9a-f]{64})</code>',text)
        vuln=re.search(r'Vulnerabilities:</dt>\s*<dd[^>]*>(.*?)</dd>',text,re.S)
        if not version or not sha: raise ValueError('version or digest field missing')
        result['catalog_version']=html.unescape(version.group(1).strip()); result['catalog_sha256']=sha.group(1)
        result['exact_snapshot_match']=(result['catalog_version']==pkg['version'] and result['catalog_sha256']==pkg['sha256_declared'])
        result['vulnerability_section_present']=bool(vuln)
        result['catalog_cves']=sorted(set(re.findall(r'CVE-\d{4}-\d{4,}',vuln.group(1)))) if vuln else []
        result['status']='ok'
    except Exception as e: result['status']='error';result['error']=type(e).__name__+': '+str(e)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=sorted(pool.map(scan,packages),key=lambda p:p['name'])
out={'source':'https://packages.msys2.org/packages/','retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'Read-only catalog version/hash exact match and CVE extraction; no binaries executed, no complete vulnerability scan','packages':results}
Path('docs/evidence/t014-transitive/catalog-review.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('total',len(results),'ok',sum(x['status']=='ok' for x in results),'exact',sum(x.get('exact_snapshot_match',False) for x in results),'cves',sum(bool(x.get('catalog_cves')) for x in results),'errors',sum(x['status']=='error' for x in results))
