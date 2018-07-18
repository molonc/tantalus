

# Check 1: ok
for bamfile in BamFile.objects.exclude(read_groups__dna_library__library_type='SC_WGS'):
    samples = bamfile.get_samples()
    if len(samples) != 1:
        continue
    sample_id = samples[0].sample_id

    libraries = bamfile.get_libraries()
    if len(libraries) != 1:
        continue
    library_id = libraries[0].library_id

    a, b, c, _ = bamfile.bam_file.filename.split('/', 3)

    if a!= sample_id or (b != library_id and c != library_id):
        print sample_id, library_id, bamfile.bam_file.filename



# Check 2: 
for bamfile in BamFile.objects.exclude(read_groups__dna_library__library_type='SC_WGS'):
    samples = bamfile.get_samples()
    libraries = bamfile.get_libraries()

    if len(samples) == 0 or len(libraries) == 0:
        print bamfile.bam_file.filename, bamfile.get_storage_names()


# Check 3: 
for bamfile in BamFile.objects.exclude(read_groups__dna_library__library_type='SC_WGS'):
    samples = bamfile.get_samples()
    libraries = bamfile.get_libraries()

    if len(samples) > 1 or len(libraries) > 1:
        print bamfile.bam_file.filename, bamfile.get_storage_names()


# Check 4: 
name_check = collections.defaultdict(list)
i = 0
for bamfile in BamFile.objects.filter(read_groups__dna_library__library_type='SC_WGS').distinct():
    if i % 1000 == 0:
        print i
    i += 1
    samples = get_samples(bamfile)
    libraries = get_libraries(bamfile)

    if len(samples) != 1 or len(libraries) != 1:
        continue

    sample = samples[0]
    library = libraries[0]
    lanes = get_lanes_str(SequenceLane, bamfile)

    index_sequences = set()
    for readgroup in bamfile.read_groups.all():
        index_sequences.add(readgroup.index_sequence)
    assert len(index_sequences) == 1
    index_sequence = list(index_sequences)[0]

    name = 'BAM-{}-{}-{}-{} ({})'.format(
        sample.sample_id,
        library.library_type,
        library.library_id,
        lanes,
        index_sequence,
    )

    name_check[name].append(bamfile)

    if len(name_check[name]) > 1:
        print bamfile.id

for name in name_check:
    if len(name_check[name]) > 1:
        print name, bamfile.bam_file.filename





for bamfile in BamFile.objects.exclude(read_groups__dna_library__library_type='SC_WGS'):
    samples = bamfile.get_samples()
    if len(samples) == 1:
        sample = samples[0]
    elif len(samples) == 0:
        sample = Sample.objects.get(sample_id=sample_id)

    libraries = bamfile.get_libraries()
    if len(libraries) == 1:
        library = libraries[0]
    elif len(libraries) == 0:
        library = DNALibrary.objects.get(library_id=library_id)

    print sample_id, library_id, bamfile.bam_file.filename

    if len(samples) > 1 or len(libraries) > 1:
        print bamfile.bam_file.filename
        break

    name = '_'.join([
        sample.sample_id,
        library.library_type,
        library.library_id,
    ])
    print name

    alignment, _ = Alignment.objects.get_or_create(
        reference_genome=bamfile.reference_genome,
        aligner=bamfile.aligner,
    )

    sequencedataset, _ = SequenceDataset.objects.get_or_create(
        dataset_type='BAM',
        sample=sample,
        library=library,
        alignment=alignment,
        name=name,
    )

    for file_resource in bamfile.file_resources.all():
        sequencedataset.file_resources.add(file_resource)

    for readgroup in bamfile.read_groups.all():
        lane, _ = SequencingLane.objects.get_or_create(
            flowcell_id=readgroup.sequence_lane.flowcell_id,
            lane_number=readgroup.sequence_lane.lane_number,
            dna_library=library,
            sequencing_centre=readgroup.sequence_lane.sequencing_centre,
            sequencing_instrument=readgroup.sequence_lane.sequencing_instrument,
            sequencing_library_id=readgroup.sequencing_library_id,
            read_type=readgroup.sequence_lane.read_type,
        )
        sequencedataset.sequence_lanes.add(lane)

    for t in bamfile.tags.all():
        sequencedataset.tags.add(t)


for bamfile in BamFile.objects.filter(read_groups__dna_library__library_type='SC_WGS'):
    samples = bamfile.get_samples()
    if len(samples) == 1:
        sample = samples[0]
    elif len(samples) == 0:
        sample = Sample.objects.get(sample_id=sample_id)

    libraries = bamfile.get_libraries()
    if len(libraries) == 1:
        library = libraries[0]
    elif len(libraries) == 0:
        library = DNALibrary.objects.get(library_id=library_id)

    lanes =  sorted(bamfile.read_groups.values_list('sequence_lane', flat=True).distinct())
    lanes = ', '.join([str(SequenceLane.objects.get(id=a)) for a in lanes])

    if len(samples) > 1 or len(libraries) > 1:
        print bamfile.bam_file.filename
        break

    name = '{}-{}-{} ({})'.format(
        sample.sample_id,
        library.library_type,
        library.library_id,
        lanes,
    )

    alignment, _ = Alignment.objects.get_or_create(
        reference_genome=bamfile.reference_genome,
        aligner=bamfile.aligner,
    )

    sequencedataset, _ = SequenceDataset.objects.get_or_create(
        dataset_type='BAM',
        sample=sample,
        library=library,
        alignment=alignment,
        name=name,
    )

    index_sequences = set()
    for readgroup in bamfile.read_groups.all():
        lane, _ = SequencingLane.objects.get_or_create(
            flowcell_id=readgroup.sequence_lane.flowcell_id,
            lane_number=readgroup.sequence_lane.lane_number,
            dna_library=library,
            sequencing_centre=readgroup.sequence_lane.sequencing_centre,
            sequencing_instrument=readgroup.sequence_lane.sequencing_instrument,
            sequencing_library_id=readgroup.sequencing_library_id,
            read_type=readgroup.sequence_lane.read_type,
        )
        sequencedataset.sequence_lanes.add(lane)
        index_sequences.add(readgroup.index_sequence)

    assert len(index_sequences) == 1
    index_sequence = list(index_sequences)[0]

    for file_resource in bamfile.file_resources.all():
        assert file_resource.index_sequence is None or file_resource.index_sequence == index_sequence
        file_resource.index_sequence = index_sequence
        sequencedataset.file_resources.add(file_resource)

    for t in bamfile.tags.all():
        sequencedataset.tags.add(t)


for fq in PairedEndFastqFiles.objects.filter(read_groups__dna_library__library_type='SC_WGS'):
    samples = fq.get_samples()
    if len(samples) == 1:
        sample = samples[0]
    elif len(samples) == 0:
        sample = Sample.objects.get(sample_id=sample_id)

    libraries = fq.get_libraries()
    if len(libraries) == 1:
        library = libraries[0]
    elif len(libraries) == 0:
        library = DNALibrary.objects.get(library_id=library_id)

    lanes =  sorted(fq.read_groups.values_list('sequence_lane', flat=True).distinct())
    lanes = ', '.join([str(SequenceLane.objects.get(id=a)) for a in lanes])

    if len(samples) > 1 or len(libraries) > 1:
        print fq.bam_file.filename
        break

    index_sequences = set()
    for readgroup in fq.read_groups.all():
        index_sequences.add(readgroup.index_sequence)
    assert len(index_sequences) == 1
    index_sequence = list(index_sequences)[0]

    name = '{}-{}-{}-{} ({})'.format(
        sample.sample_id,
        library.library_type,
        library.library_id,
        index_sequence,
        lanes,
    )

    sequencedataset, _ = SequenceDataset.objects.get_or_create(
        dataset_type='FQ',
        sample=sample,
        library=library,
        name=name,
    )

    for readgroup in fq.read_groups.all():
        lane, _ = SequencingLane.objects.get_or_create(
            flowcell_id=readgroup.sequence_lane.flowcell_id,
            lane_number=readgroup.sequence_lane.lane_number,
            dna_library=library,
            sequencing_centre=readgroup.sequence_lane.sequencing_centre,
            sequencing_instrument=readgroup.sequence_lane.sequencing_instrument,
            sequencing_library_id=readgroup.sequencing_library_id,
            read_type=readgroup.sequence_lane.read_type,
        )
        sequencedataset.sequence_lanes.add(lane)

    for file_resource in fq.file_resources.all():
        assert file_resource.index_sequence is None or file_resource.index_sequence == index_sequence
        file_resource.index_sequence = index_sequence
        sequencedataset.file_resources.add(file_resource)

    for t in fq.tags.all():
        sequencedataset.tags.add(t)
