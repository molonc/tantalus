library(stringr)
library(plyr)

tops <- list.files("/share/lustre/projects/single_cell_indexing/pipeline_inbox", full.names = TRUE)
mids <- list.files(tops, full.names = TRUE, pattern = "bcl2fastq")

output <- data.frame()

for (mid in mids) {
	print(mid)

	files <- list.files(mid, pattern = ".fastq.gz", recursive = TRUE, full.names = TRUE)

	library_id <- str_extract(files, "SC-\\d+")



	# hit <- str_detect(basename(files), "SA\\d+-A\\d+-R\\d+-C\\d+_S\\d+_R\\d+_\\d+.fastq.gz")

	# if (all(hit)) {
	# 	print("7 column")

	# 	parse <- subset(files, hit)
	# 	bases <- basename(parse)

	# 	df <- as.data.frame(str_split_fixed(bases, "[_-]", 7))
	# 	names(df) <- c("library_id", "external_id", "row", "col", "cell", "read", "ext")
	# 	df$ext <- NULL
	# 	df$path <- parse

	# } else {

	# 	print("8 column")
	# 	hit <- str_detect(basename(files), "SA\\S+-\\S+-A\\d+-R\\d+-C\\d+_S\\d+_R\\d+_\\d+.fastq.gz")

	# 	parse <- subset(files, hit)
	# 	bases <- basename(parse)

	# 	df <- as.data.frame(str_split_fixed(bases, "[_-]", 8))
	# 	names(df) <- c("library_id", "external_id2", "external_id", "row", "col", "cell", "read", "ext")
	# 	df$ext <- NULL
	# 	df$path <- parse
	# }

	# head(bases)

	# output <- rbind.fill(output, df)
	# print(dim(output))


}
