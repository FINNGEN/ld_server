task import_vcf {

    File vcf
    String vcf_base = basename(vcf, ".vcf.gz")

    command <<<
        tomahawk import -i ${vcf} -o ${vcf_base}.twk
    >>>

    output {
        File twk = vcf_base + ".twk"
        File mapping = vcf_base + ".twk.mapping.txt"
    }

    runtime {
        docker: "gcr.io/finngen-refinery-dev/tomahawk:beta-0.7.1-dirty-fg-v1"
        cpu: 1
        memory: "3G"
        disks: "local-disk 200 SSD"
        preemptible: 1
    }
}

task collect_mappings {

    Array[File] mappings
    String out_name

    command <<<
        cat <(head -1 ${mappings[0]}) \
        <(for file in ${sep=" " mappings}; do tail -n+2 $file; done) \
        | bgzip > ${out_name}

        tabix -s1 -b2 -e2 ${out_name}
    >>>

    output {
        File out = out_name
        File out_tbi = out_name + ".tbi"
    }

    runtime {
        docker: "gcr.io/finngen-refinery-dev/bioinformatics:0.5"
        cpu: 1
        memory: "3G"
        disks: "local-disk 200 SSD"
        preemptible: 1
    }
}

workflow tomahawk_import {

    File vcf_list
    Array[String] vcfs = read_lines(vcf_list)

    scatter (vcf in vcfs) {
        call import_vcf {
            input: vcf=vcf
        }
    }

    call collect_mappings {
        input: mappings = import_vcf.mapping
    }
}
