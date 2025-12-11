terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

 # backend "s3" {
    # !!! bunları KENDİ hesabına göre dolduracaksın
 #   bucket         = "distributedai-terraform-state"   # S3 bucket adın
 #   key            = "eks/terraform.tfstate"           # state dosyası yolu
 #   region         = "eu-central-1"                    # bucket bölgesi
 #   dynamodb_table = "distributedai-terraform-locks"   # optional: state lock tablosu
 #   encrypt        = true
 # }
}

provider "aws" {
  region = var.aws_region

  # Dry-run / local plan modunda metadata’ya gitme:
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
}
