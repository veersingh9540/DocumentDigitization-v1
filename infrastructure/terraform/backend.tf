terraform {
  backend "s3" {
    bucket = "document-processing-tf-state"
    key    = "terraform/state"
    region = "us-east-1"
  }
}
