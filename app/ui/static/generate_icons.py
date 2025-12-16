#!/usr/bin/env python3
"""
Generate PWA icons as actual PNG files using minimal PNG encoding
"""
import os
import struct
import zlib

def create_png(width, height, color_rgb):
    """Create a minimal solid-color PNG"""
    # PNG signature
    png = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data
    ihdr += struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    png += ihdr
    
    # IDAT chunk - image data
    raw_data = b''
    r, g, b = color_rgb
    for y in range(height):
        raw_data += b'\x00'  # filter type
        raw_data += bytes([r, g, b]) * width
    
    compressed = zlib.compress(raw_data, 9)
    idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed
    idat += struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff)
    png += idat
    
    # IEND chunk
    iend = struct.pack('>I', 0) + b'IEND'
    iend += struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    png += iend
    
    return png

# Icon sizes
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

# Create icons directory
icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(icons_dir, exist_ok=True)

# Blue color matching theme
blue_rgb = (59, 130, 246)  # #3b82f6

# Generate all sizes
for size in sizes:
    png_data = create_png(size, size, blue_rgb)
    output_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
    
    with open(output_path, 'wb') as f:
        f.write(png_data)
    
    print(f'Created: {output_path} ({len(png_data)} bytes)')

print('All PNG icons generated successfully!')
