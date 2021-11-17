import hdlparse.verilog_parser as vlog
import re

def parseAllStatements(ignore):
    f = open("spm.synthesis.v", "r").read()
    
    statements = []
    prevI = 0
    curStatement = ""
    for i in range(len(f)):
        if f[i]==";":
            curStatement=f[prevI:i+1]
            found = False
            for curIgnore in ignore:
                if curStatement.find(curIgnore) != -1:
                    found = True
            if found==False:
                curStatement = curStatement.lstrip()
                statements.append(curStatement)
            prevI=i+1
    return statements
    

def parseSiteWidth():
    f = open("merged_unpadded.lef", "r").read()
    s = f[f.find("unithd"):]
    return float(s[s.find("SIZE")+5:s.find("BY")-1])*1000

def parseUnitHeight():
    f = open("merged_unpadded.lef", "r").read()
    s = f[f.find("unithd"):]
    return float(s[s.find("BY")+3:s[s.find("BY"):s.find("BY")+10].find(";")+s.find("BY")-1])*1000

def parseHeader(file,vlogModules):
    header = 'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\n'
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
        tempS = "ROW ROW_"+str(i)+" unithd " + str(powerRingWidth) + " "
        tempS += str(int(initialHeight+i*unitHeight)) 
        if i%2==0:
            tempS += " N "
        else:
            tempS += " FS "
        tempS += "DO " +str(horizontalLoop) + " BY 1 STEP " 
        tempS += str(int(siteWidth)) + " 0"
        tempS += "\n"
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

    file.write("NETS " + str(len(occ))+" ; \n")

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


    file.write("END NETS \nEND DESIGN \n")
        
def calculateNumOfPins(vlogModules): 
    
    numberOfports = 0 


    for i in vlogModules: 
        for j in i.ports: 
            numberOfports = numberOfports + 1
            if(j.data_type!=""):
                toint = j.data_type.split(":")
                fixed = toint[0][2:] 
    
                numberOfports+=int(fixed)
    return numberOfports

def parseComponents(file):
    statements = parseAllStatements(["module","wire","input","output"])

    file.write("COMPONENTS "+str(len(statements))+" ;\n")
    for cur in statements:
        file.write("-")
        file.write(cur[cur.find(" "):cur.find("(")])
        file.write(cur[0:cur.find(" ")])
        file.write(" ;\n")

    file.write("END COMPONENTS \n")

def parsePins(file,vlogModules):
    
    numberOfPins = calculateNumOfPins(vlogModules) 
    file.write("PINS "+str(numberOfPins)+" ;\n")

    for i in vlogModules:
        for m in i.ports: 
            if(m.data_type==""): 
                
                file.write("- " + m.name + " + NET " + m.name + " + DIRECTION INPUT + USE SIGNAL\n + PORT\n   + LAYER metx ( 0 0 ) ( 0 0 )\n  + PLACED ( 0 0 ) N ;\n")

            else:
                toint = m.data_type.split(":")
                fixed = toint[0][2:] 
                nLoop = int(fixed)
                for k in range(nLoop+1): 

                    file.write("- " + m.name +"["+str(k)+"]"+ " + NET " + m.name +"["+str(k)+"]"+ " + DIRECTION INPUT + USE SIGNAL\n + PORT\n   + LAYER metx ( 0 0 ) ( 0 0 )\n   + PLACED ( 0 0 ) N ;\n")
                    # file.write(m.name+"["+str(k)+"]\n")  
    file.write("END PINS \n")   


def calcArea():
    f = open("merged_unpadded.lef", "r").read()
    macrosDimensions = {}
    macros = [_.start() for _ in re.finditer("MACRO", f)]
    for i in range(0,len(macros)):
        substr = f[macros[i]:len(f)]
        macroName = substr[6:substr.find("\n")].strip()
        sizeStatement = substr[substr.find("SIZE"):len(f)]
        width = 1000*float(sizeStatement[sizeStatement.find("SIZE")+5:sizeStatement.find("BY")])
        height = 1000*float(sizeStatement[sizeStatement.find("BY")+3:sizeStatement.find(";")])
        macrosDimensions[macroName] = (width,height)
    
    statements = parseAllStatements(["module","wire","input","output"])
    totalArea = 0
    for cur in statements:
        curComponent = cur[0:cur.find(" ")]
        totalArea += macrosDimensions[curComponent][0]*macrosDimensions[curComponent][1]

    print(totalArea)
    return totalArea

def main():
     vlog_ex = vlog.VerilogExtractor()
     vlogModules = vlog_ex.extract_objects("spm.synthesis.v")
     f = open("floorplan.def", "a")
     parseHeader(f,vlogModules)
     f.write("DIEAREA ( 0 0 ) ( 98990 109710 ) ;\n") #To be checked later
     parseRows(f)
     parseComponents(f)
     parsePins(f,vlogModules)
     parseNets(f)
     f.close()
     calcArea()
main()