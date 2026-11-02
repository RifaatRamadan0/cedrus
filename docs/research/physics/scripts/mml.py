import re,sys
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
s=open(sys.argv[1],encoding='utf-8').read()
def lin(e):
    t=e.tag.split('}')[-1]; ch=list(e)
    if t in('mi','mn','mo','mtext'): return (e.text or '').strip()
    if t=='mfrac': return '('+lin(ch[0])+')/('+lin(ch[1])+')'
    if t=='msup': return lin(ch[0])+'^('+lin(ch[1])+')'
    if t=='msub': return lin(ch[0])+'_'+lin(ch[1])
    if t=='msubsup': return lin(ch[0])+'_'+lin(ch[1])+'^('+lin(ch[2])+')'
    if t=='msqrt': return 'sqrt('+' '.join(lin(c) for c in ch)+')'
    if t=='mfenced': return (e.get('open','('))+','.join(lin(c) for c in ch)+(e.get('close',')'))
    if t=='mover': return lin(ch[0])+'~'
    if t=='munder' or t=='munderover': return lin(ch[0])+'['+' '.join(lin(c) for c in ch[1:])+']'
    return ' '.join(lin(c) for c in ch)
for m in re.finditer(r'<disp-formula.*?</disp-formula>',s,re.S):
    f=m.group(0)
    for mm in re.finditer(r'<mml:math.*?</mml:math>',f,re.S):
        x=mm.group(0)
        x=re.sub(r'<mml:math[^>]*>','<math xmlns:mml="m">',x,1).replace('</mml:math>','</math>')
        try:
            r=ET.fromstring(x.replace('mml:',''))
            print(re.sub(r'\s+',' ',lin(r)))
        except Exception as ex: print('ERR',ex)
    print('---')
