/* Byte-preserving INI edits. Buffer limit is explicit, never truncate a file. */
#define ICAP 16000
typedef struct {char *p;unsigned n;} INI;
static int last_sections;
static int foldcmp(const char *a,const char *b){unsigned char x,y;while(*a&&*b){x=*a++;y=*b++;if(x>=128||y>=128){if(x!=y||*a!=*b)return 1;if(*a){a++;b++;}}else if(toupper(x)!=toupper(y))return 1;}return *a!=*b;}
static INI imem(const char *p,unsigned n){INI x;if(n>ICAP)die("INI/group too large");x.p=malloc(ICAP+1);if(!x.p)die("Not enough conventional memory");memcpy(x.p,p,n);x.p[n]=0;x.n=n;return x;}
static INI iread(const char *path){FILE *f=fopen(path,"rb");INI x=imem("",0);int n;if(!f){if(errno!=ENOENT)die("Cannot read INI/group");return x;}n=fread(x.p,1,ICAP+1,f);fclose(f);if(n>ICAP)die("INI/group exceeds safe limit");x.n=n;x.p[n]=0;return x;}
static void ireplace(INI *x,unsigned a,unsigned b,const char *v,unsigned n){if(a>b||b>x->n||x->n-b+a+n>ICAP)die("INI bounds");memmove(x->p+a+n,x->p+b,x->n-b);memcpy(x->p+a,v,n);x->n=x->n-b+a+n;x->p[x->n]=0;}
/* Collect exact raw key lines. Duplicate owned sections are a conflict. */
static int ilines(INI *x,const char *sec,const char *key,unsigned *starts,unsigned *ends,char vals[16][256],unsigned *insert){unsigned at=0,end,len;int active=0,sections=0,count=0;char line[512],section[100],*q,*eq;
*insert=x->n;while(*insert&&((unsigned char)x->p[*insert-1]==26))--*insert;
while(at<x->n&&(unsigned char)x->p[at]!=26){end=at;while(end<x->n&&x->p[end]!='\n'&&(unsigned char)x->p[end]!=26)end++;len=end-at;if(len&&x->p[at+len-1]=='\r')len--;if(len>=sizeof(line))die("INI line too long");memcpy(line,x->p+at,len);line[len]=0;q=line;while(*q==' '||*q=='\t')q++;
if(*q=='['&&(eq=strchr(q,']'))!=NULL){*eq=0;if(strlen(q+1)>=sizeof(section))die("INI section too long");strcpy(section,q+1);active=!foldcmp(section,sec);if(active){if(++sections>1)die("Duplicate owned INI section");*insert=end<x->n&&x->p[end]=='\n'?end+1:end;}}
else if(active){*insert=end<x->n&&x->p[end]=='\n'?end+1:end;if(*q!=';'&&(eq=strchr(q,'='))!=NULL){*eq++=0;while(strlen(q)&&isspace((unsigned char)q[strlen(q)-1]))q[strlen(q)-1]=0;if(!foldcmp(q,key)){if(count>=16||strlen(eq)>255)die("INI duplicate/value overflow");starts[count]=at;ends[count]=end<x->n&&x->p[end]=='\n'?end+1:end;strcpy(vals[count++],eq);}}}
at=end<x->n&&x->p[end]=='\n'?end+1:end;if(end==at&&at<x->n&&(unsigned char)x->p[at]==26)break;}
last_sections=sections;return count;}
static void iset(INI *x,const char *sec,const char *key,const char *wanted,int kind,const char *suffix){unsigned st[16],en[16],ins;char vals[16][256],line[512];int i,n=ilines(x,sec,key,st,en,vals,&ins);(void)kind;(void)suffix;if(n==1&&!foldcmp(vals[0],wanted))return;
sprintf(line,"%s=%s\r\n",key,wanted);if(n){for(i=n-1;i>0;i--)ireplace(x,st[i],en[i],"",0);ireplace(x,st[0],en[0],line,strlen(line));}
else{{unsigned a[16],b[16],where;char vv[16][256];ilines(x,sec,"__GB6_NO_KEY__",a,b,vv,&where);ins=where;}
if(ins&&x->p[ins-1]!='\n'){ireplace(x,ins,ins,"\r\n",2);ins+=2;}
if(!last_sections){char header[140];sprintf(header,"\r\n[%s]\r\n",sec);ireplace(x,ins,ins,header,strlen(header));ins+=strlen(header);}

ireplace(x,ins,ins,line,strlen(line));}}
static int iget(INI *x,const char *s,const char *k,char *v){unsigned a[16],b[16],z;char vals[16][256];int n=ilines(x,s,k,a,b,vals,&z);if(n==1)strcpy(v,vals[0]);return n;}
/* Restore only keys changed by us, and only while current values match post. */
static void irestore(INI *before,INI *post,INI *cur){unsigned at=0,end;char sec[100]="",line[512],key[256],*eq,*q;unsigned a[16],b[16],z,pa[16],pb[16],ba[16],bb[16];char vals[16][256],pv[16][256],bv[16][256];int n,pn,bn,i,same;
while(at<post->n&&(unsigned char)post->p[at]!=26){end=at;while(end<post->n&&post->p[end]!='\n')end++;if(end-at>=sizeof(line))die("INI restore line overflow");memcpy(line,post->p+at,end-at);line[end-at]=0;q=line;while(*q==' '||*q=='\t')q++;if(*q=='['&&(eq=strchr(q,']'))!=NULL){*eq=0;if(strlen(q+1)>=sizeof(sec))die("INI section too long");strcpy(sec,q+1);}else if(*sec&&*q!=';'&&(eq=strchr(q,'='))!=NULL){*eq=0;if(strlen(q)>=sizeof(key))die("INI key too long");strcpy(key,q);pn=ilines(post,sec,key,pa,pb,pv,&z);bn=ilines(before,sec,key,ba,bb,bv,&z);same=pn==bn;for(i=0;same&&i<pn;i++)if(strcmp(pv[i],bv[i]))same=0;if(!same){n=ilines(cur,sec,key,a,b,vals,&z);same=n==pn;for(i=0;same&&i<n;i++)if(strcmp(vals[i],pv[i]))same=0;if(same){for(i=n-1;i>=0;i--)ireplace(cur,a[i],b[i],"",0);if(bn)ireplace(cur,a[0],a[0],before->p+ba[0],bb[0]-ba[0]);/* known duplicate old values restored below */
if(bn>1){unsigned where=a[0]+bb[0]-ba[0];for(i=1;i<bn;i++){ireplace(cur,where,where,before->p+ba[i],bb[i]-ba[i]);where+=bb[i]-ba[i];}}}
else note("CONFLICT KEEP user-modified INI key %s/%s\n",sec,key);}}
at=end<post->n?end+1:end;}}
