options(stringsAsFactors = FALSE)
library(stringr)
library(plyr)

dirs <- list.files("/share/lustre/archive", full.names = TRUE)

missed <- 0
hit <- 0

output <- data.frame()

ignore <- c()

# for (i in 1:length(dirs)) {
for (i in 1:length(dirs)) {
	dir <- dirs[i]
	base <- basename(dir)

	if (str_detect(base, "^SA\\d+") |
		str_detect(base, "^DAH\\d+") |
		str_detect(base, "^TK\\d+") |
		str_detect(base, "^DG\\d+") |
		str_detect(base, "^DLC\\d+") |
		str_detect(base, "^FL\\d+") |
		str_detect(base, "^\\d+") |
		str_detect(base, "^TN\\d+") |
		str_detect(base, "^Dedhar\\S+") |
		str_detect(base, "^STG\\d+") |
		str_detect(base, "^A\\d+") |
		str_detect(base, "^POG\\d+") |
		str_detect(base, "^SEO\\S+") |
		str_detect(base, "^RG\\d+")) {
		files <- list.files(dir, recursive = TRUE, pattern = ".bam$")

		if (length(files) == 0) {
			next
		}

		for (file in files) {

			tokens <- unlist(strsplit(file, "/"))
			if (length(tokens) == 4) {
				df <- as.data.frame(str_split_fixed(file, "/", 4))
				names(df) <- c("library_type", "library_id", "file_type", "file")
				df$sample_id <- basename(dir)
				df$path <- paste0(dir, "/", file)
				df$notes <- ""
				output <- rbind.fill(output, df)
				# print(df)
				hit <- hit + 1
			} else if (length(tokens) == 5) {
				df <- as.data.frame(str_split_fixed(file, "/", 5))
				names(df) <- c("library_type", "library_id", "file_type", "notes", "file")
				df$sample_id <- basename(dir)
				df$path <- paste0(dir, "/", file)
				output <- rbind.fill(output, df)
				# print(df)
				hit <- hit + 1				
			} else {
				print(dir)
			}

		}
	} else {
		ignore <- c(ignore, dir)
		missed <- missed + 1
	}
}

print(hit)
print(missed)

print(table(output$library_type))
# print(table(output$library_id))
print(table(output$file_type))

output$bytes <- file.size(output$path)
output <- output[, c("sample_id", "library_type", "library_id", "file_type", "file", "bytes", "path", "notes")]

write.table(output, sep = "\t", row.names = FALSE, quote = FALSE, file = "bulk_bam.txt")
