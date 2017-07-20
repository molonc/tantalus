library(plyr)
options(stringsAsFactors = FALSE)

dirs <- list.files("/share/lustre/archive/single_cell_indexing/HiSeq", full.names = TRUE)
dirs <- grep("old", dirs, invert = TRUE, value = TRUE)
dirs <- grep("PX", dirs, value = TRUE)


output <- data.frame()

for (dir in dirs) {
	print(dir)

	files <- list.files(dir, recursive = TRUE, pattern = "fastq.gz$", full.names = TRUE)
	passed <- grep("failed", files, invert = TRUE, value = TRUE)
	read1 <- grep("_1_chastity|1.fastq|_1_001_", passed, value = TRUE)
	read2 <- grep("_2_chastity|2.fastq|_2_001_", passed, value = TRUE)

	tmp <- sapply(strsplit(read1, "/"), "[[", 8)

	flowcell <- sapply(strsplit(tmp, "_"), head, 1)
	lane <- sapply(strsplit(tmp, "_"), tail, 1)

	tmp <- sapply(strsplit(read1, "/"), "[[", 9)

	id <- sapply(strsplit(tmp, "[_-]"), "[[", 1)
	code1 <- sapply(strsplit(tmp, "[_-]"), "[[", 2)
	code2 <- sapply(strsplit(tmp, "[_-]"), "[[", 3)

	if (any(id == "s")) {
		id <- sapply(strsplit(read1, "/"), "[[", 7)
		code1 <- sapply(strsplit(basename(read1), "[._-]"), "[[", 5)
		code2 <- sapply(strsplit(basename(read1), "[._-]"), "[[", 6)
	}

	centre <- "Genome Science Centre"
	df <- data.frame(id, flowcell, lane, centre, code1, code2, read1, read2)
	print(head(df, 1))
	output <- rbind.fill(output, df)
	print(dim(output))
}

write.table(output, sep = "\t", row.names = FALSE, quote = FALSE, file = "single_cell_hiseq_fastq.txt")
