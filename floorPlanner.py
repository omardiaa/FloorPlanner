import hdlparse.verilog_parser as vlog

def parseSiteWidth():
    f = open("merged_unpadded.lef", "r").read()
    s = f[f.find("unithd"):]
    return float(s[s.find("SIZE")+5:s.find("BY")-1])*1000

def parseUnitHeight():
    f = open("merged_unpadded.lef", "r").read()
    s = f[f.find("unithd"):]
    return float(s[s.find("BY")+3:s[s.find("BY"):s.find("BY")+10].find(";")+s.find("BY")-1])*1000


def parseHeader(vlogModules):
    header = 'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]";\n'
    header += "DESIGN "+vlogModules[0].name+";\nUNITS DISTANCE MICRONS 1000 ;\n"
    return header

def parseRows():
    totalWidth = 98990
    powerRingWidth = 5520
    siteWidth = parseSiteWidth()
    unitHeight = parseUnitHeight()
    rowsCount = 32
    initialHeight = 10880 

    horizontalLoop = int((totalWidth - 2*(powerRingWidth)) / (siteWidth))
    for i in range(0,rowsCount):
        print("ROW ROW_",str(i)," unithd " , powerRingWidth ,
             int(initialHeight+i*unitHeight) , " N "if i%2==0 else" FS "\
                  , "DO " , horizontalLoop , " BY 1 STEP " ,\
                       int(siteWidth) , " 0")



def main():
    vlog_ex = vlog.VerilogExtractor()
    vlogModules = vlog_ex.extract_objects("spm.synthesis.v")
    print(parseHeader(vlogModules))
    print("DIEAREA ( 0 0 ) ( 98990 109710 ) ;")#To be checked later
    print(parseRows())

main()