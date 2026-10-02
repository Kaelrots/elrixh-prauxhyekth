"""Conservative Clausewitz text parser: preserves duplicate assignments and missing values."""
import re
from dataclasses import dataclass

@dataclass
class Token:
    value: str
    start: int
    end: int
    line: int
    quoted: bool=False

@dataclass
class Node:
    entries: list
    start: int=0
    end: int=0

@dataclass
class Typed:
    kind: str
    value: object

TOKEN=re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|[{}]|\?=|!=|<=|>=|[=<>!?]|[^\s{}=<>!?#"]+')

def atom(t):
    if t.quoted:
        return re.sub(r'\\(["\\])',r'\1',t.value[1:-1])
    if re.fullmatch(r'-?\d+',t.value): return int(t.value)
    if re.fullmatch(r'-?\d+\.\d+',t.value): return float(t.value)
    return t.value

class Parser:
    def __init__(self,text,path):
        self.text=text;self.path=path;self.issues=[];self.i=0
        self.tokens=[];line=1;last=0
        for m in TOKEN.finditer(text):
            line+=text[last:m.start()].count('\n');last=m.start()
            if not m.group().startswith('#'): self.tokens.append(Token(m.group(),m.start(),m.end(),line,m.group().startswith('"')))
    def warning(self,t,kind,detail): self.issues.append(dict(source_file=self.path,line=t.line,kind=kind,detail=detail))
    def parse(self): return self.block(False)
    def block(self,braced):
        start=self.tokens[self.i].start if self.i<len(self.tokens) else 0
        if braced:self.i+=1
        rows=[]
        while self.i<len(self.tokens):
            t=self.tokens[self.i]
            if t.value=='}':
                self.i+=1
                if not braced:
                    self.warning(t,'unexpected_close','Unmatched closing brace; continued at top level')
                    continue
                return Node(rows,start,t.end)
            if self.i+1<len(self.tokens) and self.tokens[self.i+1].value in ['=','<','>','<=','>=','!=','?=']:
                op=self.tokens[self.i+1].value;self.i+=2
                if self.i==len(self.tokens) or self.tokens[self.i].value=='}' or (self.i+1<len(self.tokens) and self.tokens[self.i+1].value in ['=','<','>','<=','>=','!=','?=']):
                    val=None;self.warning(t,'missing_assignment_value',t.value+' '+op)
                else:val=self.value()
                rows.append((str(atom(t)),op,val,t.line))
            else:
                rows.append((None,None,self.value(),t.line))
        if braced:self.warning(self.tokens[-1],'unclosed_block','Missing closing brace')
        return Node(rows,start,len(self.text))
    def value(self):
        t=self.tokens[self.i]
        if t.value=='{':return self.block(True)
        self.i+=1
        if not t.quoted and t.value in ('rgb','hsv','hsv360') and self.i<len(self.tokens) and self.tokens[self.i].value=='{':return Typed(t.value,self.block(True))
        return atom(t)

def values(node,key): return [v for k,o,v,l in node.entries if k==key] if isinstance(node,Node) else []
def get(node,key,default=None):
    v=values(node,key);return v[-1] if v else default
def items(node): return [v for k,o,v,l in node.entries if k is None] if isinstance(node,Node) else []
def keys(node): return [k for k,o,v,l in node.entries if k is not None] if isinstance(node,Node) else []
def plain(value):
    if isinstance(value,Typed): return {'type':value.kind,'value':plain(value.value)}
    if isinstance(value,Node):
        if all(k is None for k,o,v,l in value.entries):return [plain(v) for k,o,v,l in value.entries]
        return {'assignments':[{'key':k,'operator':o,'value':plain(v),'line':l} for k,o,v,l in value.entries]}
    return value
def dictionary(node):
    result={}
    if not isinstance(node,Node):return result
    for k,o,v,l in node.entries:
        if k is not None:
            if k in result:result[k]={'repeated_values':[result[k],plain(v)]}
            else:result[k]=plain(v)
    return result

def hexcode(v):
    if isinstance(v,str) and re.fullmatch(r'(?:x|X|#)?[0-9a-fA-F]{6}',v):return re.sub(r'^[xX#]','',v).upper()
    return None

if __name__=='__main__':
    import pathlib,collections,json
    root=pathlib.Path(__file__).resolve().parent.parent/'source_snapshot';summary={};issues=[];fieldcounts=collections.Counter();states=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix not in ['.txt','.map','.heightmap','.info']:continue
        rel=p.relative_to(root).as_posix();parser=Parser(p.read_text(encoding='utf-8-sig'),rel);node=parser.parse();issues+=parser.issues
        summary[rel]=len(node.entries)
        if '/state_regions/' in rel:
            for k,o,v,l in node.entries:
                if k and k.startswith('STATE_'):states.append((k,get(v,'id'),len(items(get(v,'provinces')))));fieldcounts.update(keys(v))
    print(json.dumps({'file_counts':summary,'state_count':len(states),'state_fields':fieldcounts,'empty_states':sum(n==0 for k,i,n in states),'issues':issues},ensure_ascii=False,indent=2))
