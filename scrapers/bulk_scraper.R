options(stringsAsFactors = FALSE)
library(stringr)

dirs <- list.files("/share/lustre/archive", full.names = TRUE)

missed <- 0
hit <- 0

for (dir in dirs) {
	base <- basename(dir)

	if (str_detect(base, "SA\\d+")) {
		files <- list.files(dir, recursive = TRUE)
		for (file in files) {

			dirpath <- dirname(file)
			filepath <- basename(file)

			dirbits <- unlist(strsplit(dirpath, "/"))
			for (dirbit in dirbits) {
				
			}

			stop()
		}
	} else {
		missed <- missed + 1
	}
}

print(hit)
print(missed)
