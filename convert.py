# -*- coding: utf-8 -*-
# 
from PIL import Image
from argparse import ArgumentParser
import sys

# Colour mapping
COLOURS = {(255,255,255):0,
          (0,0,0):1,
          (0,0,255):2,
          (0,128,0):3,
          (255,0,0):4,
          (128,64,64):5,
          (128,0,255):6,
          (128,128,0):7,
          (255,255,79):8,
          (0,255,0):9,
          (0,128,128):10,
          (0,255,255):11,
          (0,0,255):12,
          (255,0,255):13,
          (128,128,128):14,
          (192,192,192):15,}

           
# Special case the solid block as we have to override the foreground
SOLID = (0,0,0,0)

# Transparency masks and display characters
MASKS = {SOLID: '▖',
         (1,1,0,1): '▜',
         (0,1,1,1): '▟',
         (0,1,1,0): '▞',
         (1,1,1,0): '▛',
         (1,0,1,1): '▙'}

# Full set of possible substitutions
SUBSTITUTIONS = []
for c1 in COLOURS:
    for c2 in COLOURS:
        for mask in MASKS:
            # (Background, Foreground), Mask
            SUBSTITUTIONS.append(((c1,c2),mask))


class Transform(object):
    
    def substitute(self,block):
        """ Match a substitution to block """
        best = None
        result = None
        for substitution in SUBSTITUTIONS:
            colours,mask = substitution
            error = 0
            for index in xrange(4):
                # This lets the mask specify which bits are transparent
                colour = colours[mask[index]]
                for channel in xrange(3):
                    error += abs(block[index][channel] - colour[channel])
            if best is None or error < best:
                best = error
                result = substitution

        return result
    
    def convert(self,fp,size):
        image = Image.open(fp)
        #100,64
        image.thumbnail(size)

        # Our pixels are 2*1, so we need to (roughly) double the width
        width,height = image.size
        sys.stderr.write("Thumbnail size: %sx%s\n" % (width,height))
        
        image = image.resize((width*2, height), Image.ANTIALIAS)

        # These may be different to what we asked for above
        width,height = image.size
        source = list(image.getdata())

        # Rather than dealing with half height blocks, just ditch them
        width = (width/2)*2
        height = (height/2)*2

        result = []
        for y in xrange(0,height,2):
            row = []
            for x in xrange(0,width,2):
                offset = (y * width) + x

                block = [source[offset],
                         source[offset+1],
                         source[offset+width],
                         source[offset+width+1]]

                substitution = self.substitute(block)
                row.append(substitution)

            result.append(row)

        return result
    
    def render_irc(self,converted):
        result = ""
        
        compressed = []
        for row in converted:
            last = [None,0]
            compressed_row = []
            for substitution in row:
                if last[0] == substitution:
                    last[1] += 1
                else:
                    if last[0] is not None:
                        compressed_row.append(last)
                    last = [substitution,1]
            
            if last[0] is not None:
                compressed_row.append(last)
            compressed.append(compressed_row)

        max_length = 0
        
        for row in compressed:
            line = ""
            for substitution,count in row:
                background = COLOURS[substitution[0][0]]
                foreground = COLOURS[substitution[0][1]]

                # Solid mask says we should always use the background colour
                if substitution[1] is SOLID:
                    foreground = background

                character = MASKS[substitution[1]]

                line += "\x03%s,%s%s" % (foreground,background,character * count)
            
            length = len(line) + 1 # +1 for newline
            if length > max_length:
                max_length = length
                
            result += line + '\n'
        
        sys.stderr.write("Max line length (anything over 468 is likely to break): %s\n" % max_length)
        
        return result
    
    def render_raw(self,converted):
        result = ""
        for row in converted:
            for substitution in row:
                result += MASKS[substitution[1]]
            result += '\n'
        return result
    
    def render_html(self,converted):
        result = ['''<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body { line-height:12px; font-size:12px }</style></head><body>''']
        for row in converted:
            for substitution in row:
                (foreground,background),mask = substitution
                character = MASKS[mask]
                

                if substitution is SOLID:
                    foreground = background
                
                result.append("<span style='background:rgb%s;color:rgb%s'>%s</span>" % (str(background),str(foreground),character))
            result.append("<br/>")
        result.append("</body></html>")
        return "".join(result)
        
        

if __name__ == '__main__':
    
    transform = Transform()
    
    parser = ArgumentParser()
    parser.add_argument("filename",help="image filename")
    parser.add_argument("--format", action="store",
                        default="irc",help="output format, 'html', 'irc' or 'raw'")
    parser.add_argument("--width", action="store", type=int,
                        default=100,help="max width")
    parser.add_argument("--height", action="store", type=int,
                        default=64,help="max height")


    args = parser.parse_args()
    
    
    fp = open(args.filename)
    converted = transform.convert(fp,(args.width,args.height))
    
    if args.format == 'irc':
        print transform.render_irc(converted)
    elif args.format == 'raw':
        print transform.render_raw(converted)
    elif args.format == 'html':
        print transform.render_html(converted)

