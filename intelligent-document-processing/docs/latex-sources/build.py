import re, sys, os
base = os.path.dirname(os.path.abspath(__file__))
def read(p): return open(os.path.join(base,p), encoding='utf-8').read()
def inline(s):
    # inline \input{figs/..}, \input{name}
    def rep(m):
        name=m.group(1)
        fn = name if name.endswith('.tex') else name+'.tex'
        return inline(read(fn))
    return re.sub(r'\\input\{((?:figs/)?(?:fig|m_|cover|master|p1_)[^}]*)\}', rep, s)
def build(parts, out, title):
    pre = read('preamble.tex')
    body = ''.join(read(p)+'\n' for p in parts)
    doc = ("\\documentclass[11pt,a4paper]{report}\n" + pre + "\n"
           "\\hypersetup{pdftitle={%s},pdfauthor={Tuheu Tchoubi Pempeme Moussa Fahdil}}\n" % title +
           "\\begin{document}\n" + body + "\n\\end{document}\n")
    doc = inline(doc)
    open(os.path.join(base,'..',out),'w',encoding='utf-8').write(doc)
if __name__=='__main__':
    which = sys.argv[1]
    if which=='master':
        build(['cover_master.tex','master_front.tex','m_ch1_3.tex','m_ch4_5.tex','m_ch6_8.tex','m_ch9_14.tex','m_ch15_end.tex'],'DocuMind_AI_Project_Design_Document.tex','DocuMind AI - Project Design Document')
    elif which=='phase1':
        build(['cover_p1.tex','p1_front.tex','p1_body.tex'],'DocuMind_AI_Phase1_Requirements_Specification.tex','DocuMind AI - Phase 1 Requirements Specification')
