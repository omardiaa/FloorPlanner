import hdlparse.verilog_parser as vlog
import re

def parseSiteWidth():
    f = open("merged_unpadded.lef", "r").read()
    s = f[f.find("unithd"):]
    return float(s[s.find("SIZE")+5:s.find("BY")-1])*1000

def parseUnitHeight():
    f = open("merged_unpadded.lef", "r").read()
    s = f[f.find("unithd"):]
    return float(s[s.find("BY")+3:s[s.find("BY"):s.find("BY")+10].find(";")+s.find("BY")-1])*1000

def parseHeader(file,vlogModules):
    header = 'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]";\n'
    header += "DESIGN "+vlogModules[0].name+";\nUNITS DISTANCE MICRONS 1000 ;\n"
    file.write(header)

def parseRows(file):
    totalWidth = 98990
    powerRingWidth = 5520
    siteWidth = parseSiteWidth()
    unitHeight = parseUnitHeight()
    rowsCount = 32
    initialHeight = 10880 

    horizontalLoop = int((totalWidth - 2*(powerRingWidth)) / (siteWidth))
    for i in range(0,rowsCount):
        tempS = "ROW ROW_"+str(i)+" unithd " + str(powerRingWidth) + \
             str(int(initialHeight+i*unitHeight)) + " N "if i%2==0 else" FS "\
                  + "DO " +str(horizontalLoop) + " BY 1 STEP " +\
                       str(int(siteWidth)) + " 0"
        tempS+="\n"
        file.write(tempS)

def getWireName(s):
    return s[s.find(" ")+1:s.find(";")]

def parseNets(file):
    f = open("spm.synthesis.v", "r").read()
    f = f.replace("\\","!!") #To avoid using backslashes which causes problems with python
    f = f.replace("[","==") #To avoid using [ which causes problems with python
    f = f.replace("]","@@") #To avoid using ] which causes problems with python
    #The previous code assumes that !!, ==, @@ are never used in .v files

    occ = [_.start() for _ in re.finditer("wire", f)] 
    for i in range(0,len(occ)-1):
        netString = " - "

        wire = getWireName(f[occ[i]:occ[i+1]])
        wireOcc = [_.start() for _ in re.finditer(wire, f)]
        tempWire = wire.replace("!!","\\").replace("==","[").replace("@@","]")
        
        netString += tempWire

        tempNetStrings=[]
        for j in range(1, len(wireOcc)): #Loop on all occurances of the wire and ignore the first one
            counter = 2
            k = wireOcc[j]
            curInput = f[k-19+f[k-20:k].rfind("."):k-1]
            while(counter!=0):
                if f[k]=="(":
                    counter-=1
                if f[k]==")":
                    counter+=1
                k-=1
            moduleName = f[k-19+f[k-20:k].rfind(" "):k]
            tempNetStrings.append(" ("+moduleName + " " + curInput+") ")
        
        for j in range(len(tempNetStrings)-1,-1,-1):
            netString += tempNetStrings[j]
        netString += " + USE SIGNAL ;\n"
        file.write(netString)
        

    # print(getWireName(f[occ[len(occ)-1]:len(f)]))
    

def main():
    vlog_ex = vlog.VerilogExtractor()
    vlogModules = vlog_ex.extract_objects("spm.synthesis.v")
    f = open("floorplan.def", "a")
    parseHeader(f,vlogModules)
    f.write("DIEAREA ( 0 0 ) ( 98990 109710 ) ;") #To be checked later
    parseRows(f)
    parseNets(f)
    f.close()
    
main()