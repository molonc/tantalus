#Built from the following documentation:
#https://docs.microsoft.com/en-ca/azure/storage/storage-python-how-to-use-blob-storage

from azure.storage.blob import BlockBlobService
ACCOUNT="singlecellstorage"
KEY="okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="

def get_service():
    block_blob_service = BlockBlobService(account_name=ACCOUNT, account_key=KEY)
    return block_blob_service

def main():
    #create container
    service = get_service()
    service.create_container("testcontainer")

    #upload a file to the container
    service.create_blob_from_path(
        "testcontainer",
        "blob-test-code",
        "blob_demo.py")

    #list blobs
    for blob in service.list_blobs("testcontainer"):
        print(blob.name)

    #download blob
    service.get_blob_to_path("testcontainer","blob-test-code","blob_output.txt")

    #delete blob
    service.delete_blob("testcontainer","blob-test-code")

if __name__=="__main__":
    main()

