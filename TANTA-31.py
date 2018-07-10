

for b in BamFile.objects.filter(read_groups=None):
    sample_id = b.bam_file.filename.split('/')[0]
    library_id = b.bam_file.filename.split('/')[2]
    Sample.objects.get(sample_id=sample_id)
    DNALibrary.objects.get(library_id=library_id)


bamtype = SequenceDatasetType(name='BAM')
bamtype.save()

for b in BamFile.objects.all():
    samples = b.get_samples()
    libraries = b.get_libraries()
	if

	if len(samples) != 1 or len(libraries) != 1:
		print b.bam_file.filename
		continue

    name = ' '.join([
        sample.sample_id,
        library.library_id,
    ])
    print name

    alignment = Alignment(
        reference_genome=b.reference_genome,
        aligner=b.aligner,
    )
    alignment.save()

    s = SequenceDataset(
        dataset_type=bamtype,
        sample=sample,
        library=library,
        alignment=alignment,
        name=b.get_name(),
    )
    s.save()

    for file_resource in b.file_resources.all():
        sf = SequenceFileResource(file_resource=file_resource)
        sf.save()
        s.sequence_file_resources.add(sf)

    for rg in b.read_groups.all():
        s.sequence_lanes.add(rg.sequence_lane)



fastqtype = SequenceDatasetType(name='Paired End FASTQ')
