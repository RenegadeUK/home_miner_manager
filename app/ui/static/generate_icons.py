#!/usr/bin/env python3
"""
Generate PWA icons with cool miner design
Uses SVG as base and converts to PNG sizes
"""
import os
import subprocess

def create_svg_icon(size):
    """Generate SVG icon with scalable design"""
    # Scale factors
    s = size / 512  # Base design is 512x512
    
    svg = f'''<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg{size}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6"/>
      <stop offset="100%" style="stop-color:#2563eb"/>
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="{size}" height="{size}" rx="{int(90*s)}" fill="url(#bg{size})"/>
  
  <!-- Pickaxe -->
  <g transform="translate({size/2},{180*s}) rotate(-25)">
    <rect x="{-15*s}" y="0" width="{30*s}" height="{180*s}" fill="#64748b" rx="{5*s}"/>
    <rect x="{-80*s}" y="{-25*s}" width="{160*s}" height="{35*s}" fill="#94a3b8" rx="{8*s}"/>
    <path d="M {-80*s},{-8*s} L {-120*s},{-8*s} L {-110*s},{-25*s} L {-80*s},{-15*s} Z" fill="#cbd5e1"/>
  </g>
  
  <!-- BTC Circle -->
  <circle cx="{size/2}" cy="{380*s}" r="{75*s}" fill="#fbbf24"/>
  
  <!-- BTC Symbol -->
  <text x="{size/2}" y="{380*s}" font-family="Arial,sans-serif" font-size="{100*s}" font-weight="bold" fill="white" text-anchor="middle" dominant-baseline="central">₿</text>
  
  <!-- Hash symbols -->
  <text x="{100*s}" y="{140*s}" font-family="monospace" font-size="{30*s}" fill="white" opacity="0.5">#</text>
  <text x="{size-100*s}" y="{160*s}" font-family="monospace" font-size="{25*s}" fill="white" opacity="0.4">#</text>
</svg>'''
    
    return svg

# Icon sizes
sizes = [72, 96, 128, 144, 152, 192, 384, 512]

# Create icons directory
icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(icons_dir, exist_ok=True)

print('Generating icon SVGs...')

for size in sizes:
    svg_content = create_svg_icon(size)
    svg_path = os.path.join(icons_dir, f'icon-{size}x{size}.svg')
    png_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
    
    # Save SVG
    with open(svg_path, 'w') as f:
        f.write(svg_content)
    
    # Try to convert to PNG using available tools
    converted = False
    
    # Try rsvg-convert (librsvg)
    try:
        subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), svg_path, '-o', png_path], 
                      check=True, capture_output=True)
        converted = True
        print(f'✓ Created PNG: {png_path}')
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try ImageMagick convert
    if not converted:
        try:
            subprocess.run(['convert', svg_path, png_path], check=True, capture_output=True)
            converted = True
            print(f'✓ Created PNG: {png_path}')
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
    # If no converter available, keep SVG (browsers can use it)
    if not converted:
        # Rename SVG to PNG - modern browsers accept SVG in PWA manifest
        os.rename(svg_path, png_path)
        with open(png_path, 'w') as f:
            f.write(svg_content)
        print(f'ℹ Created SVG-as-PNG: {png_path} (install ImageMagick or librsvg for real PNGs)')

print('\nAll icons generated!')
