
import math
import io
# https://github.com/tomchen/bdfparser
from bdfparser import Font, Glyph, Bitmap

class BitmapAdv(Bitmap):
    '''
    Subclass for Bitmap with helper methods
    '''
    def __init__(self, bin_bitmap_list):
        super().__init__(bin_bitmap_list)
    
    @classmethod
    def fromParent(cls, parent : Bitmap):
        return cls(parent.bindata)
    
    def transpose(self):
        '''
        Transpose bitmap around top-left corner
        '''
        data = self.todata(2)
        transpData = [''.join(map(str, row)) for row in zip(*data)]
        self.bindata = transpData
    
    def flipHorizontal(self):
        self.bindata = [row[::-1] for row in self.bindata]
    
    def flipVertical(self):
        self.bindata.reverse()
    
    def rotateCW(self):
        self.transpose()
        self.flipHorizontal()
        
    def rotateCCW(self):
        self.transpose()
        self.flipVertical()

    def getCArr(self, orderIsRowMajor : bool = True) -> list[str]:
        '''
        Convert this bitmap to data for entry in C array. 
        Top row of pixels are each LSB of different entries.
        Args:
        - orderIsRowMajor - byte order in array, row major ('Z') or column major ('|/|')
        Return - byte array as a list of HEX strings
        '''
        
        # Prepare char for conversion to bytes - 
        # rotate so top-left pixel is last in 1st row
        rotatedBmap = self.clone()
        rotatedBmap.rotateCW()
        
        # Get bytes, with LSB being rightmost column, padded with leading zeros
        data = rotatedBmap.todata(4)
        
        # Split into individual bytes
        byteArr = []
        nibblesAmt = 2      # Amount of hex symbols per C array entry
        for row in data:
            rowArr = []
            for i in range(0, len(row), nibblesAmt):
                rowArr.append(row[i:i+nibblesAmt])
            rowArr.reverse()
            byteArr.append(rowArr)
        
        # Convert from column-major to row-major order
        if(orderIsRowMajor):
            byteArr = [list(row) for row in zip(*byteArr)]
        
        # Flatten 2D list into list of strings
        flatByteArr = [elem for row in byteArr for elem in row]
        return flatByteArr
    
    def doPadding(self, top : int, bottom : int, left : int, right : int):
        '''
        Add blank bits to side if positive padding, remove if negative
        '''
        if(top > 0):
           self.bindata = top * ['0' * self.width()] + self.bindata
        elif(top < 0):
            self.bindata = self.bindata[-top:]
        
        if(bottom > 0):
            self.bindata = self.bindata + bottom * ['0' * self.width()]
        elif(bottom < 0):
            self.bindata = self.bindata[:bottom]
        
        if(left > 0):
            self.bindata = [('0' * left) + row for row in self.bindata]
        elif(left < 0):
            self.bindata = [row[-left:] for row in self.bindata]
        
        if(right > 0):
            self.bindata = [row + ('0' * right) for row in self.bindata]
        elif(right < 0):
            self.bindata = [row[:right] for row in self.bindata]

class GlyphProcessor:
    '''
    Converter to turn char Glyphs into C array elements with desired 
    padding/trimming, row/column order, rotation/mirroring.
    '''   

    def __init__(self):
        # bitmap padding or trim (positive for padding)
        self.padding = {
            "Top":      0,
            "Bottom":   0,
            "Left":     0,
            "Right":    0
        }
        self.arrElemStructName = "fontGlyphEntry_t"
        self.arrName = "fontArray"
        self.setDataOrderRowMajor()
        self.mirrorHoriz = False
        self.mirrorVert = False
        self.rotationCount = 0

    def setPaddingTop(self, pad : int):
        '''
        Positive value for padding, negative value for trimming, in Pixels
        '''
        self.padding["Top"] = pad

    def setPaddingBottom(self, pad : int):
        '''
        Positive value for padding, negative value for trimming, in Pixels
        '''
        self.padding["Bottom"] = pad

    def setPaddingLeft(self, pad : int):
        '''
        Positive value for padding, negative value for trimming, in Pixels
        '''
        self.padding["Left"] = pad

    def setPaddingRight(self, pad : int):
        '''
        Positive value for padding, negative value for trimming, in Pixels
        '''
        self.padding["Right"] = pad

    def setDataOrderRowMajor(self):
        '''
        Set data order for conversion of bitmap to array. 
        Only matters for 2-row high fonts
        '''
        self.dataOrderIsRowMajor = True

    def setDataOrderColumnMajor(self):
        '''
        Set data order for conversion of bitmap to array. 
        Only matters for 2-row high fonts
        '''
        self.dataOrderIsRowMajor = False

    def doHorizontalMirror(self):
        '''
        Enable horizontal mirroring.
        Order of operations - padding, mirroring, rotation
        '''
        self.mirrorHoriz = True

    def doVerticalMirror(self):
        '''
        Enable vertical mirroring.
        Order of operations - padding, mirroring, rotation
        '''
        self.mirrorVert = True
    
    def rotateCW(self):
        '''
        Rotate clockwise by 90 deg. Can be repeated.
        Order of operations - padding, mirroring, rotation
        '''
        self.rotationCount += 1
    
    def rotateCCW(self):
        '''
        Rotate counter-clockwise by 90 deg. Can be repeated.
        Order of operations - padding, mirroring, rotation
        '''
        self.rotationCount -= 1
        
    def glyphToBitmap(self, glyph: Glyph) -> Bitmap:
        '''
        Get transformed bitmap from glyph. 
        Order of operations - padding, mirroring, rotation
        '''
        bmapPlus = BitmapAdv.fromParent(glyph.draw())
        # Do padding
        bmapPlus.doPadding(self.padding["Top"], self.padding["Bottom"], self.padding["Left"], self.padding["Right"])
        # Do mirroring
        if(self.mirrorHoriz):
            bmapPlus.flipHorizontal()
        if(self.mirrorVert):
            bmapPlus.flipVertical()
        # Do rotations
        rotation = self.rotationCount % 4
        for _ in range(0, rotation, 1):
            bmapPlus.rotateCW()
        # Repack into regular bitmap
        return Bitmap(bmapPlus.bindata)

    def glyphToCEntry(self, glyph: Glyph) -> str:
        '''
        Convert glyph into entry for C array.
        Return - "{    97, { 0x00, 0x01, 0x02, 0x03, 0x04, 0x05 } }"
        '''
        bmapPlus = BitmapAdv.fromParent(self.glyphToBitmap(glyph))
        data = bmapPlus.getCArr(self.dataOrderIsRowMajor)
        cArr = "{ 0x"
        cArr += ", 0x".join(data)
        cArr += " }"
        cEntry = f"{{ {glyph.cp():>5}, {cArr} }}"
        return cEntry

    def getEntryComment(self, charcode : int) -> str:
        '''
        Get a comment for array entry. 
        Example: "' a ' (0x0061)"
        '''
        # Get char if not control code
        charSymbol = ' '
        if(charcode >= ord(' ')):
            charSymbol = chr(charcode)
        comm = f"\' {charSymbol} \' (0x{charcode:04X})"
        return comm

    def getArrStructTypedef(self, baseGlyph: Glyph) -> str:
        '''
        Construct pre-array code
        Args:
        - baseGlyph - any glyph from font, for reference
        '''
        baseBmap = self.glyphToBitmap(baseGlyph)
        byteHeight = math.ceil(float(baseBmap.height()) / 8.0)
        byteSize = baseBmap.width() * byteHeight
        
        return "#include <stdint.h>\n"\
            "\n"\
            f"#define GLYPH_WIDTH    {baseBmap.width()}\n"\
            f"#define GLYPH_SIZE     {byteSize}\n"\
            "\n"\
            "typedef struct {\n"\
            "    uint16_t charCode;\n"\
            "    uint8_t data[GLYPH_SIZE];\n"\
            f"}} {self.arrElemStructName};"

    def getArrHeader(self) -> str:
        return f"const static {self.arrElemStructName} {self.arrName}[] = {{"

    def getArrFooter(self) -> str:
        return "};"


def fontToCArray(outputHFile : str, inputFontFile : str, glyphProc : GlyphProcessor, charCodes : list[tuple[int, int]]):
    '''
    Convert select glyphs from font file into C array, write to a file
    Args:
    - outputHFile - path to output .h file. Gets overwritten or created
    - inputFontFile - path to .bdf font file
    - glyphProc - preconfigured GlyphProcessor object for font adjustment
    - charCodes - list of tuples, each tuple has 2 ints for start/end of range in UTF-16 (inclusive). 
        Pass None to process full font
    '''
    
    font = Font(inputFontFile)
    print(f"This font's global size is "
        f"{font.headers['fbbx']} x {font.headers['fbby']} (pixel), "
        f"it contains {len(font)} glyphs.")
    print(font.headers)
    
    # Print struct and array definitions
    outBuf = io.StringIO()
    outBuf.write(glyphProc.getArrStructTypedef(next(font.iterglyphs())) + '\n\n')
    outBuf.write(glyphProc.getArrHeader() + '\n')
    
    # Print array itself
    glyphCount = 0
    for glyph in font.iterglyphs(order=1, r=charCodes):
        glyphCount += 1
        arrEntry = glyphProc.glyphToCEntry(glyph)
        arrComment = glyphProc.getEntryComment(glyph.cp())
        
        fullEntry = f"{arrEntry}, // {arrComment}"
        outBuf.write("\t" + fullEntry + "\n")
    print("Glyphs in array: " + str(glyphCount))
    
    # Print array footer
    outBuf.write(glyphProc.getArrFooter() + "\n")
    
    # Print buffer into file (create or erase file)
    with open(outputHFile, 'w', encoding="utf-8") as outFile:
        outFile.write(outBuf.getvalue())



def main():
    
    # Example 1 - 6x9 font cut cown to 6x8, full font
    
    outFilename = './examples/5x8_full.h'
    fontFilename = './misc-misc/6x9.bdf'
 
    glyphProc = GlyphProcessor()
    glyphProc.setPaddingTop(-1)
    
    fontToCArray(outFilename, fontFilename, glyphProc, None)
    
    # Example 2 - 8x13 font scaled to 8x16, ASCII + Cyrillic + Misc Symbols
    
    outFilename = './examples/8x16_vert.h'
    fontFilename = './misc-misc/8x13.bdf'
    
    charlist = list()
    charlist.append((0x0000, 0x007F))  # ASCII
    charlist.append((0x0400, 0x04FF))  # Cyrillic
    charlist.append((0x2600, 0x26FF))  # Misc Symbols
    
    glyphProc = GlyphProcessor()
    glyphProc.setPaddingTop(3)
    glyphProc.setDataOrderRowMajor()
    
    fontToCArray(outFilename, fontFilename, glyphProc, charlist)
    
    # Example 3 - 8x13 font, rotatedm +90deg, in column-major order
    
    outFilename = './examples/8x13_horiz.h'
    fontFilename = './misc-misc/8x13.bdf'
    
    charlist = list()
    charlist.append((0x0000, 0x007F))  # ASCII
    charlist.append((0x0400, 0x04FF))  # Cyrillic
    charlist.append((0x2600, 0x26FF))  # Misc Symbols
    
    glyphProc = GlyphProcessor()
    glyphProc.setDataOrderColumnMajor()
    glyphProc.rotateCCW()
    
    fontToCArray(outFilename, fontFilename, glyphProc, charlist)



if(__name__ == "__main__"):
    main()
