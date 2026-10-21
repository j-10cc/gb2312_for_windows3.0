/* DOS 8086: install SHELL terminology without losing Setup registration. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define REG_AT 6048L
#define REG_LEN 96
static unsigned char reg[REG_LEN],block[8192];

int main(int argc,char **argv)
{
    FILE *in,*out; char dest[128],tmp[128],bak[128],*dot;
    const char *source; long at=0; unsigned n,k; int ok=1;
    if(argc!=3||strlen(argv[2])>110)return 20;
    source=!strcmp(argv[1],"CGA")?"ZHRES\\SHELL.CGA":"ZHRES\\SHELL.DLL";
    strcpy(dest,argv[2]);strcpy(tmp,dest);dot=strrchr(tmp,'.');
    if(!dot)return 20;strcpy(dot,".GTR");
    strcpy(bak,dest);dot=strrchr(bak,'.');strcpy(dot,".GTO");
    in=fopen(dest,"rb");if(!in)return 20;
    if(fseek(in,REG_AT,SEEK_SET)||fread(reg,1,REG_LEN,in)!=REG_LEN){fclose(in);return 20;}
    fclose(in);
    in=fopen(tmp,"rb");if(in){fclose(in);return 20;}
    in=fopen(bak,"rb");if(in){fclose(in);return 20;}
    in=fopen(source,"rb");if(!in)return 20;
    out=fopen(tmp,"wb");if(!out){fclose(in);return 20;}
    while((n=fread(block,1,sizeof(block),in))!=0){
        for(k=0;k<n;k++)if(at+k>=REG_AT&&at+k<REG_AT+REG_LEN)
            block[k]=reg[(unsigned)(at+k-REG_AT)];
        if(fwrite(block,1,n,out)!=n){ok=0;break;}at+=n;
    }
    if(ferror(in))ok=0;
    if(fclose(out))ok=0;fclose(in);
    if(!ok){remove(tmp);return 20;}
    if(rename(dest,bak)){remove(tmp);return 20;}
    if(rename(tmp,dest)){rename(bak,dest);return 20;}
    remove(bak);return 0;
}
