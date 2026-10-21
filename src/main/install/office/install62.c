/* DOS5-R4: direct file copies and required configuration. No content verification. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <dos.h>
#include <direct.h>
#include <io.h>
#include <process.h>
#include <sys/stat.h>
static FILE *trace;
static void note(const char *fmt,...);
static void die(const char *s){printf("ERROR: %s\n",s);if(trace){fprintf(trace,"ERROR: %s\r\n",s);fflush(trace);}exit(20);}
static char office[80],windows[80],media[128],tx[128];
static int pathsyntax(const char *s,unsigned limit){unsigned i=3,n,a,b;char part[16];if(strlen(s)>limit||!isalpha((unsigned char)s[0])||s[1]!=':'||s[2]!='\\'||!s[3])return 0;
while(s[i]){n=0;a=0;b=0;while(s[i]&&s[i]!='\\'){unsigned char c=s[i++];if(c>=128){if(c<0xA1||c>0xF7||(unsigned char)s[i]<0xA1||(unsigned char)s[i]>0xFE||n>10)return 0;part[n++]=c;part[n++]=s[i++];if(!b)a+=2;continue;}if(n>=12||c<=32||strchr("/:*?\"<>|+,;=[]",c))return 0;part[n++]=c;if(c=='.'){if(b)return 0;b=1;}else if(!b)a++;}part[n]=0;if(!a||a>8||n-a-(b?1:0)>3||part[n-1]=='.')return 0;{char stem[16],*p;strcpy(stem,part);p=strchr(stem,'.');if(p)*p=0;if(!stricmp(stem,"CON")||!stricmp(stem,"PRN")||!stricmp(stem,"AUX")||!stricmp(stem,"NUL")||((!strnicmp(stem,"COM",3)||!strnicmp(stem,"LPT",3))&&strlen(stem)==4&&stem[3]>='1'&&stem[3]<='9'))return 0;}if(s[i]=='\\'&&!s[++i])return 0;}return 1;}
static int pathok(const char *s){return pathsyntax(s,70);}

#include "ini62.h"
#include "group64.h"
typedef struct {long off;const char *suffix;} SLOT;
typedef struct {const char *source,*target;int mode,shared;SLOT slot[3];} RULE;
#include "tables62.h"
#define MAXJ 48
#define SHARED 1
#define CONFIG 2
#define GROUP 4
#define PMINI 8
#define TAG 16
/* Retain old record sizes so old interrupted installs can be recovered. */
typedef struct {char dst[100],src[128],before[65],after[65];long size,oldsize;unsigned flags,attr;int rule;} JOB;
typedef struct {char magic[16],win[80],off[80],video[8];unsigned count;} INFO;
static INFO info;
static JOB *job;
static char *data[MAXJ];
static unsigned datalen[MAXJ],count,step;
static int video,unused,group_kept,kept;
static unsigned char buf[8192];
static int exists(const char *p){return access(p,0)==0;}
static int isdir(const char *p){struct stat st;return !stat(p,&st)&&(st.st_mode&S_IFDIR);}
static void note(const char *fmt,...){va_list ap;va_start(ap,fmt);vprintf(fmt,ap);va_end(ap);}
static void tick(const char *what){printf("STEP %u %s\n",++step,what);}
static void join(char *out,const char *a,const char *b){if(strlen(a)+strlen(b)+2>127)die("Path too long");sprintf(out,"%s\\%s",a,b);}
static void parent(char *p){char *q=strrchr(p,'\\');if(!q)die("Missing parent");*q=0;}
static void makedirs(const char *p){char x[128];unsigned i;strcpy(x,p);for(i=3;;i++){if(x[i]=='\\'||!x[i]){char c=x[i];x[i]=0;if(!exists(x)&&mkdir(x))die("Cannot create directory");x[i]=c;if(!c)break;}}}
static void closefile(FILE *f){if(fflush(f))die("Write flush failed");if(fclose(f))die("File close failed");}
static void rawwrite(const char *p,const void *d,unsigned n){FILE *f=fopen(p,"wb");if(!f||fwrite(d,1,n,f)!=n)die("Write failed (disk full/write protection)");closefile(f);}
static void marker(const char *name,const char *value){char p[128];join(p,tx,name);rawwrite(p,value,strlen(value));}
static int marked(const char *name){char p[128];join(p,tx,name);return exists(p);}
static void bkpath(char *p,unsigned i,int post){char n[16];sprintf(n,"%c%04u.%s",post?'P':'B',i,post?"PST":"BAK");join(p,tx,n);}
static int slotpatch(RULE *r,long pos,unsigned char *block,unsigned n,int canon){unsigned s,i;for(s=0;s<3&&r->slot[s].off>=0;s++){long at=r->slot[s].off;char value[80];sprintf(value,"%s%s",canon?"C:\\WINDOWS":windows,r->slot[s].suffix);if(strlen(value)>=80)die("Runtime path slot too long");for(i=0;i<n;i++)if(pos+i>=at&&pos+i<at+80)block[i]=(pos+i-at<(long)strlen(value))?value[(unsigned)(pos+i-at)]:0;}return 1;}
static void copyfile(const char *src,const char *dst,int rule){FILE *a,*b;unsigned n;long pos=0;char path[128];a=fopen(src,"rb");if(!a){printf("SOURCE %s\n",src);die("Cannot open source");}strcpy(path,dst);parent(path);makedirs(path);b=fopen(dst,"wb");if(!b){fclose(a);printf("TARGET %s\n",dst);die("Cannot create target");}printf("COPY %s\n",dst);while((n=fread(buf,1,sizeof(buf),a))!=0){if(rule>=0)slotpatch(&rules[rule],pos,buf,n,0);if(fwrite(buf,1,n,b)!=n)die("Copy write failed (disk full/write protection)");pos+=n;}if(ferror(a))die("Copy source read failed");if(fclose(a))die("Source close failed");closefile(b);}
static void addjob(const char *dst,const char *src,int rule,unsigned flags,INI *mem){JOB *j;if(count==MAXJ)die("Too many files");j=&job[count];memset(j,0,sizeof(*j));strcpy(j->dst,dst);if(src)strcpy(j->src,src);j->rule=rule;j->flags=flags;if(exists(dst)){strcpy(j->before,"1");_dos_getfileattr(dst,&j->attr);}if(mem){data[count]=mem->p;datalen[count]=mem->n;}printf("FILE %s\n",dst);count++;}
static void configs(void){char p[128],v[100],desc[256];INI x;unsigned i;static const char driverkey[]="CWIN3 BIG-5 \xBD\x58\xB4\x79\xC3\xE4\xA6\x72\xA7\xCE\xC5\x58\xB0\xCA\xB5\x7B\xA6\xA1";
if(video==1){join(p,windows,"SYSTEM.INI");x=iread(p);iset(&x,"boot","fonts.fon","cgas12.fon",1,"");addjob(p,NULL,-1,SHARED|CONFIG,&x);}
join(p,windows,"IMEINFO.INI");x=iread(p);iset(&x,"Control","installIME","1",2,"");iset(&x,"Control","EnableLHS","yes",3,"");iset(&x,"IME1","FileName","phon.ime",0,"");iset(&x,"IME1","Enable","1",2,"");i=iget(&x,"IME1","Description",desc);if(i>1)die("Duplicate IME description");if(!i||allowed_desc(desc))iset(&x,"IME1","Description",formal_desc,5,"");addjob(p,NULL,-1,SHARED|CONFIG,&x);
for(i=0;i<2;i++){join(p,windows,i?"WIFERM.INI":"WIFEMAN.INI");if(!exists(p))die("Missing WIFE native Setup config");x=iread(p);sprintf(v,"%s\\SYSTEM\\CFFONT.FOD",windows);iset(&x,"FontDrivers",driverkey,v,4,"\\SYSTEM\\CFFONT.FOD");iset(&x,"DefaultFont","FontDriver",v,4,"\\SYSTEM\\CFFONT.FOD");sprintf(v,"%s\\SYSTEM\\CFSUNG.FON",windows);iset(&x,"DefaultFont","FontPackage",v,4,"\\SYSTEM\\CFSUNG.FON");sprintf(v,"%s\\B5PART.TBL",windows);iset(&x,"DefaultFont","Big5PartialTable",v,4,"\\B5PART.TBL");sprintf(v,"%s\\SYSTEM\\CFSUNG16.B5Q",windows);iset(&x,"OutlineHandTune","CFShouSung1",v,4,"\\SYSTEM\\CFSUNG16.B5Q");sprintf(v,"%s\\SYSTEM\\CFSUNG20.B5Q",windows);iset(&x,"OutlineHandTune","CFShouSung2",v,4,"\\SYSTEM\\CFSUNG20.B5Q");addjob(p,NULL,-1,SHARED|CONFIG,&x);}}
static void groups(void){char p[128],m[128],v[256],key[30],group[100];INI cur,model,out,pm;int retained,i,found=0;join(p,windows,"COFFICE.GRP");cur=iread(p);join(m,media,video==1?"GROUP\\CGA.GRP":"GROUP\\VGA.GRP");model=iread(m);out=gmerge(&cur,&model,0,&retained);addjob(p,NULL,-1,GROUP,&out);free(cur.p);free(model.p);join(p,windows,"PROGMAN.INI");if(!exists(p))die("Missing native PROGMAN.INI");pm=iread(p);sprintf(group,"%s\\COFFICE.GRP",windows);for(i=1;i<=99;i++){sprintf(key,"Group%d",i);if(iget(&pm,"Groups",key,v)==1&&!stricmp(v,group)){found=1;break;}}if(!found){for(i=1;i<=99;i++){sprintf(key,"Group%d",i);if(!iget(&pm,"Groups",key,v))break;}if(i==100)die("No free Program Manager group slot");iset(&pm,"Groups",key,group,0,"");}addjob(p,NULL,-1,CONFIG|PMINI,&pm);}

static void saveplan(void){char p[128];FILE *f;join(p,tx,"JOBS.DAT");f=fopen(p,"wb");if(!f||fwrite(&info,1,sizeof(info),f)!=sizeof(info)||fwrite(job,sizeof(JOB),count,f)!=count)die("Cannot write recovery records");closefile(f);}
static void prepare(void){char base[128],p[128],name[20];unsigned n,i;join(base,office,"GB30TX");makedirs(base);for(n=1;n<10000;n++){sprintf(name,"T%07u",n);join(tx,base,name);if(!exists(tx))break;}if(n==10000||mkdir(tx))die("Cannot create backup directory");strcpy(info.magic,"GB30TX-6.4-N1");strcpy(info.win,windows);strcpy(info.off,office);strcpy(info.video,video==1?"CGA":"VGA");info.count=count;saveplan();join(p,office,"GB30TX\\CURRENT");rawwrite(p,name,8);tick("PREPARED");for(i=0;i<count;i++){if(job[i].before[0]){bkpath(p,i,0);copyfile(job[i].dst,p,-1);}if(data[i]&&(job[i].flags&(CONFIG|GROUP))){bkpath(p,i,1);rawwrite(p,data[i],datalen[i]);}}join(p,tx,"RECOVER.EXE");{char src[128];join(src,media,"RECOVER.EXE");copyfile(src,p,-1);}marker("READY.TAG","READY\r\n");tick("BACKED_UP");}
static void deploy(void){unsigned i;for(i=0;i<count;i++){char p[128];strcpy(p,job[i].dst);parent(p);makedirs(p);if(data[i]){printf("WRITE %s\n",job[i].dst);rawwrite(job[i].dst,data[i],datalen[i]);}else copyfile(job[i].src,job[i].dst,job[i].rule);tick("COPIED");}marker("COMMIT.TAG","INSTALLED\r\n");printf("INSTALL FINISHED %s\n",office);}
static void loadplan(void){char p[128],name[10]={0};FILE *f;unsigned i;join(p,office,"GB30TX\\CURRENT");f=fopen(p,"rb");if(!f){puts("No current transaction");exit(0);}if(fread(name,1,9,f)!=8)die("Cannot read backup directory name");fclose(f);if(name[0]!='T')die("Invalid backup directory name");for(i=1;i<8;i++)if(!isdigit(name[i]))die("Invalid backup directory name");join(p,office,"GB30TX");join(tx,p,name);join(p,tx,"JOBS.DAT");f=fopen(p,"rb");if(!f||fread(&info,1,sizeof(info),f)!=sizeof(info)||info.count>MAXJ)die("Cannot read recovery records");count=info.count;if(fread(job,sizeof(JOB),count,f)!=count)die("Cannot read recovery jobs");fclose(f);if(!memchr(info.off,0,80)||!memchr(info.win,0,80)||stricmp(info.off,office)||!pathok(info.win))die("Invalid recovery path");strcpy(windows,info.win);for(i=0;i<count;i++){if(!memchr(job[i].dst,0,100)||!pathsyntax(job[i].dst,95))die("Invalid recovery destination");if((strnicmp(job[i].dst,office,strlen(office))||job[i].dst[strlen(office)]!='\\')&&(strnicmp(job[i].dst,windows,strlen(windows))||job[i].dst[strlen(windows)]!='\\'))die("Recovery destination outside installation directories");}}
static void restorejob(unsigned i){JOB *j=&job[i];char b[128],p[128],side[128],name[16];INI pre,post,cur,out;int retained=0;if((j->flags&PMINI)&&group_kept){puts("KEEP program group registration");return;}bkpath(b,i,0);bkpath(p,i,1);
if((j->flags&(GROUP|CONFIG))&&exists(j->dst)&&exists(p)){pre=j->before[0]?iread(b):imem("",0);post=iread(p);cur=iread(j->dst);if(j->flags&GROUP){out=gundo(&cur,&pre,&post,&retained);group_kept=retained||pre.n;if(group_kept)rawwrite(j->dst,out.p,out.n);else if(remove(j->dst))die("Cannot remove group");free(out.p);}else{irestore(&pre,&post,&cur);if(!j->before[0]&&!cur.n){if(remove(j->dst))die("Cannot remove created configuration");}else rawwrite(j->dst,cur.p,cur.n);}free(pre.p);free(post.p);free(cur.p);}
else if(j->before[0]){copyfile(b,j->dst,-1);if(_dos_setfileattr(j->dst,j->attr))die("Cannot restore attributes");}else if(exists(j->dst)&&remove(j->dst))die("Cannot remove installed file");
/* Old versions may have left rename staging files; they are owned by this job. */
strcpy(side,j->dst);parent(side);sprintf(name,"G6%04u.NEW",i);join(p,side,name);if(exists(p)&&remove(p))die("Cannot remove old staging");sprintf(name,"G6%04u.OLD",i);join(p,side,name);if(exists(p)&&remove(p))die("Cannot remove old staging");tick("RESTORED_FILE");}
static void restore(void){unsigned i;int rollback;char p[128];loadplan();if(marked("RESTORED.TAG")){puts("ALREADY RESTORED");return;}if(!marked("READY.TAG")){marker("RESTORED.TAG","PREPARATION ENDED\r\n");puts("RECOVERED preparation; target files untouched");return;}rollback=!marked("COMMIT.TAG");join(p,windows,"GB30USE.TXT");if(exists(p)){INI lease=iread(p);if(lease.n)unused=0;free(lease.p);}for(i=0;i<count;i++)if(job[i].flags&GROUP)restorejob(i);for(i=count;i>0;i--){JOB *j=&job[i-1];if(j->flags&GROUP)continue;if((j->flags&SHARED)&&!unused&&!rollback){printf("KEEP shared %s\n",j->dst);kept++;continue;}restorejob(i-1);}if(!kept)marker("RESTORED.TAG","RESTORED\r\n");printf("RESTORED %s%s\n",office,kept?" (shared files retained)":"");}
int main(int argc,char **argv){char self[144],p[128],tag[180],*action;unsigned i;int cancel=0;setbuf(stdout,NULL);job=calloc(MAXJ,sizeof(JOB));if(!job)die("Not enough conventional memory");_cmdname(self);strcpy(media,self);parent(media);puts("GB Office installer DOS5-R4 (8086, direct copy)");action=strrchr(self,'\\');action=action?action+1:self;
if(!strnicmp(action,"REMOVE",6)||!strnicmp(action,"RECOVER",7)){if(argc<2||argc>3||!pathok(argv[1]))die("Usage: REMOVE/RECOVER OfficePath [UNUSED]");strcpy(office,argv[1]);if(argc==3){if(stricmp(argv[2],"UNUSED"))die("Expected UNUSED");unused=1;}restore();return 0;}
if(argc<4||argc>7)die("Usage: INSTALL CGA|VGA OfficePath WindowsPath [PROVISION|VERIFY] [UPGRADE|CANCEL]");if(!stricmp(argv[1],"CGA"))video=1;else if(!stricmp(argv[1],"VGA"))video=2;else die("Expected CGA or VGA");if(!pathok(argv[2])||!pathok(argv[3]))die("Absolute DOS 8.3 directories required");strcpy(office,argv[2]);strcpy(windows,argv[3]);if(!stricmp(office,windows)||(!strnicmp(office,windows,strlen(windows))&&office[strlen(windows)]=='\\')||(!strnicmp(windows,office,strlen(office))&&windows[strlen(office)]=='\\'))die("Use separate Windows and Office directories");if(!stricmp(media,office)||!stricmp(media,windows))die("Extract media into a separate directory");for(i=4;i<(unsigned)argc;i++){if(!stricmp(argv[i],"CANCEL"))cancel=1;else if(stricmp(argv[i],"PROVISION")&&stricmp(argv[i],"VERIFY")&&stricmp(argv[i],"UPGRADE"))die("Unknown option");}
puts("PHASE: File copy list");for(i=0;i<RULE_COUNT;i++)if(rules[i].mode&video){char a[128],b[128];join(a,media,rules[i].source);join(b,rules[i].shared?windows:office,rules[i].target);addjob(b,a,i,rules[i].shared?SHARED:0,NULL);}puts("PHASE: Required configuration");configs();groups();for(i=0;i<2;i++){char src[128];join(src,media,i?"RECOVER.EXE":"REMOVE.EXE");join(p,office,i?"RECOVER.EXE":"REMOVE.EXE");addjob(p,src,-1,0,NULL);}sprintf(tag,"GB30 6.4-N1\r\nVIDEO=%s\r\nWINDOWS=%s\r\nOFFICE=%s\r\n",video==1?"CGA":"VGA",windows,office);{INI x=imem(tag,strlen(tag));join(p,office,"GB30.TAG");addjob(p,NULL,-1,TAG,&x);}if(cancel){puts("CANCELLED");return 2;}
join(p,office,"GB30TX\\CURRENT");if(exists(p)){char n[10]={0},base[128],flag[128],done[128];FILE *f=fopen(p,"rb");if(!f||fread(n,1,9,f)!=8)die("Cannot read prior backup name");fclose(f);if(n[0]!='T')die("Invalid prior backup name");for(i=1;i<8;i++)if(!isdigit(n[i]))die("Invalid prior backup name");join(base,office,"GB30TX");join(tx,base,n);join(flag,tx,"COMMIT.TAG");join(done,tx,"RESTORED.TAG");if(!exists(flag)&&!exists(done))die("Incomplete prior installation: run RECOVER first");}
puts("PHASE: Backup existing files");prepare();puts("PHASE: Copy and configure");deploy();return 0;}
