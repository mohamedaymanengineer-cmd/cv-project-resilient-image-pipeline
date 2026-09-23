import logging
from io import BytesIO
from PIL import Image
from worker import create_thumbnail, build_thumbnail_key

logging.disable(logging.CRITICAL)

test_image = Image.new("RGB", (800, 600), color=(120, 160, 200))
buffer = BytesIO()
test_image.save(buffer, format="JPEG")
image_bytes = buffer.getvalue()

thumbnail_bytes, metadata = create_thumbnail(image_bytes)

print("== create_thumbnail ==")
print("Metadata:", metadata)
print("Thumbnail size in bytes:", len(thumbnail_bytes))

print("== build_thumbnail_key ==")
print(build_thumbnail_key("uploads/photo1.jpg"))
