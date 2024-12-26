
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

    def getCArr(self, entrySizeBytes : int = 1, orderIsRowMajor : bool = True) -> str:
        '''
        Convert this bitmap to an entry in C array. 
        Args:
        - entrySizeBytes - how many bytes per C array element. 1 is bytes, 2 is shorts
        - orderIsRowMajor - byte order in array, row major ('Z') or column major ('И')
        '''
        
        # Prepare char for conversion to bytes - 
        # rotate so top-left pixel is last in 1st row
        rotatedBmap = self.clone()
        rotatedBmap.rotateCW()
        
        # Get bytes, with LSB being rightmost column, padded with leading zeros
        data = rotatedBmap.todata(4)
        
        # Split into individual bytes
        byteArr = []
        nibblesAmt = entrySizeBytes * 2      # Amount of hex symbols per C array entry
        for row in data:
            rowArr = []
            for i in range(0, len(row), nibblesAmt):
                rowArr.append(row[i:i+nibblesAmt])
            rowArr.reverse()
            byteArr.append(rowArr)
        
        # Convert from column-major to row-major order
        if(orderIsRowMajor):
            byteArr = [list(row) for row in zip(*byteArr)]
        
        # TODO - add switch from Little Endian to Big Endian here (if needed)
        
        # Flatten 2D list into list of strings
        flatByteArr = [elem for row in byteArr for elem in row]
        
        # Convert into C array
        cArrStr = "{ 0x"
        cArrStr += ", 0x".join(flatByteArr)
        cArrStr += " }"
        return cArrStr
    
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
    padding/trimming, row/column order, data size, etc.
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
        self.setDataEntrySize(1)

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

    def setDataEntrySize(self, size : int):
        '''
        Set size of array element in bytes. 
        1 is byte array, 2 is short array, 3-4 is long array
        '''
        if((size < 1) | (size > 4)):
            raise ValueError("Element size must be 1-4 bytes")
        self.dataEntrySize = size

    def getDataEntryType(self) -> str:
        '''
        Get C type name for array element size
        '''
        dataEntryType = ""
        if(self.dataEntrySize == 1):
            dataEntryType = "uint8_t"
        elif(self.dataEntrySize == 2):
            dataEntryType = "uint16_t"
        else:
            dataEntryType = "uint32_t"
        return dataEntryType

    def glyphToBitmap(self, glyph : Glyph) -> Bitmap:
        '''
        Convert glyph into bitmap with applied padding/trimming
        '''
        bmapPlus = BitmapAdv.fromParent(glyph.draw())
        bmapPlus.doPadding(self.padding["Top"], self.padding["Bottom"], self.padding["Left"], self.padding["Right"])
        return Bitmap(bmapPlus.bindata)

    def glyphToCEntry(self, glyph : Glyph) -> str:
        '''
        Convert glyph into entry for C array.
        Example of return string:
        "{    97, { 0x00, 0x01, 0x02, 0x03, 0x04, 0x05 } }"
        '''
        bmapPlus = BitmapAdv.fromParent(self.glyphToBitmap(glyph))
        cArr = bmapPlus.getCArr(self.dataEntrySize, self.dataOrderIsRowMajor)
        cEntry = f"{{ {glyph.cp():>5}, {cArr} }}"
        return cEntry

    def getEntryComment(self, glyph : Glyph) -> str:
        '''
        Get a comment for array entry. 
        Example: "' a ' (0x0061)"
        '''
        # Get char if not control code
        charSymbol = ' '
        if(glyph.chr() >= ' '):
            charSymbol = glyph.chr()
        comm = f"\' {charSymbol} \' (0x{glyph.cp():04X})"
        return comm

    def getArrStructTypedef(self) -> str:
        dataType = self.getDataEntryType()
        return "#include <stdint.h>\n"\
            "\n"\
            "typedef struct {\n"\
            "\tchar16_t code;\n"\
            f"\t{dataType} data[];\n"\
            f"}} {self.arrElemStructName};"

    def getArrHeader(self) -> str:
        return f"const static {self.arrElemStructName} {self.arrName}[] = {{"

    def getArrFooter(self) -> str:
        return "};"


def fontToCArray(outputHFile : str, inputFontFile : str, glyphProc : GlyphProcessor, charCodes : set):
    '''
    Convert select glyphs from font file into C array, write to a file
    Args:
    - outputHFile - path to output .h file. Gets overwritten or created
    - inputFontFile - path to .bdf font file
    - glyphProc - preconfigured GlyphProcessor object for font adjustment
    - charCodes - set of character codes in UTF-16 that gets put into array. 
        Chars not present in font are skipped, warning is printed to console
    '''
    
    font = Font(inputFontFile)
    print(f"This font's global size is "
        f"{font.headers['fbbx']} x {font.headers['fbby']} (pixel), "
        f"it contains {len(font)} glyphs.")
    print(font.headers)
    
    with open(outputHFile, 'w') as file:
        pass    # erase file
    with open(outputHFile, 'a', encoding="utf-8") as outFile:
        # Print struct and array definitions
        outFile.write(glyphProc.getArrStructTypedef() + '\n\n')
        outFile.write(glyphProc.getArrHeader() + '\n')
        
        # Print array itself
        for charcode in sorted(charCodes):
            glyph = font.glyphbycp(charcode)
            if(glyph is None):
                continue
            arrEntry = glyphProc.glyphToCEntry(glyph)
            arrComment = glyphProc.getEntryComment(glyph)
            
            fullEntry = f"{arrEntry}, // {arrComment}"
            outFile.write("\t" + fullEntry + "\n")
        
        # Print array footer
        outFile.write(glyphProc.getArrFooter() + "\n")

    pass


def main():
    
    outFilename = './outArr.h'
    fontFilename = './misc-misc/6x9.bdf'
    
    charset = set()
    charset |= set(range(0x0000, 0x0080))   # ASCII
    charset |= set(range(0x0400, 0x0500))   # Cyrillic
    charset |= set(range(0x2600, 0x2700))   # Misc Symbols
    
    glyphProc = GlyphProcessor()
    glyphProc.setPaddingTop(-1)
    glyphProc.setDataOrderRowMajor()
    glyphProc.setDataEntrySize(1)
    
    fontToCArray(outFilename, fontFilename, glyphProc, charset)
    
    pass


if(__name__ == "__main__"):
    main()
