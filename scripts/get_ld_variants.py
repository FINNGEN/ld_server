#!/usr/bin/env python3
import argparse
import gzip
import requests
import sys
import time
def get_ld_vars( chrom, pos, ref, alt, r2, ld_w, retries=3):
    snooze=1
    api="http://api.finngen.fi/api/ld?variant={}:{}:{}:{}&panel=sisu3&window={}&r2_thresh={}"
    url = api.format(chrom,pos,ref,alt,ld_w,r2)
    r = requests.get(url)
    while r.status_code!=200 or retries<0:
        if r.status_code!=200:
            print("Error requesting ld for url {}. Error code: {}".format(url, r.status_code) ,file=sys.stderr)
            time.sleep(snooze)
        retries-=1
        r = requests.get(url)
    return(r.json())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', action='store', type=str, help='')
    parser.add_argument('-variant_id', default="locus_id")
    parser.add_argument('-phenoid', default="pheno")
    parser.add_argument('-ld', default=0.2)
    parser.add_argument('-ld_w', default=3000000)
    args = parser.parse_args()

    of = gzip.open if args.file.endswith(".gz") else open
    with of(args.file, 'rt') as infile:
        h = { hd:i for i,hd in enumerate(infile.readline().strip().split("\t")) }
        varcol = args.variant_id
        phenocol = args.phenoid	
        if not (varcol in h and phenocol in h):
            raise Exception("Given columns not in file")
        print("\t".join(["pheno","locus_id","ld_var","ld"]))
        for l in infile:
            dat = l.strip().split("\t")
            var = dat[h[varcol]].split("_")
            pheno = dat[h[phenocol]]
            chrom= var[0] if var[0].startswith("chr") else "chr"+var[0]
            ld_partners = get_ld_vars(chrom, var[1], var[2], var[3], args.ld, args.ld_w)
            for p in ld_partners["ld"]:
                print("\t".join([pheno,dat[h[varcol]], "chr" + p["variation2"].replace(":","_"),str(p["r2"])]))

		
		
