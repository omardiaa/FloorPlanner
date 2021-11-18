import hdlparse.verilog_parser as vlog
import re
import math 
import sys

def parseAllStatements(inputFile, ignore):
    f = open(inputFile, "r").read()
    
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
    header += "DESIGN "+vlogModules[0].name+" ;\nUNITS DISTANCE MICRONS 1000 ;\n"
    file.write(header)

def  parseRows(file, totalSites, numberOfRows,marginYBottom,marginX):
    totalWidth = totalSites  #dieArea width 
    powerRingWidth = marginX #margin
    siteWidth = parseSiteWidth()
    unitHeight = parseUnitHeight() 
    rowsCount = numberOfRows
    initialHeight = marginYBottom #ymargin 

    horizontalLoop = totalWidth
    for i in range(0,rowsCount):
        tempS = "ROW ROW_"+str(i)+" unithd " + str(powerRingWidth) + " "
        tempS += str(int(initialHeight+i*unitHeight)) 
        if i%2==0:
            tempS += " N "
        else:
            tempS += " FS "
        tempS += "DO " +str(horizontalLoop) + " BY 1 STEP " 
        tempS += str(int(siteWidth)) + " 0 ;"
        tempS += "\n"
        file.write(tempS)

def getName(s):
    return s[s.find(" ")+1:s.find(";")]

def parseNets(inputFile, file, vlogModules):
    f = open(inputFile, "r").read()
    f = f.replace("\\","!!") #To avoid using backslashes which causes problems with python
    f = f.replace("[","==") #To avoid using [ which causes problems with python
    f = f.replace("]","@@") #To avoid using ] which causes problems with python
    #The previous code assumes that !!, ==, @@ are never used in .v files

    wires = [_.start() for _ in re.finditer("wire", f)] 
    
    inputsAndOutputs = []
    for i in vlogModules: 
        for j in i.ports: 
            if(j.data_type!=""):
                toint = j.data_type.split(":")
                fixed = toint[0][2:] 
                for k in range(0,int(fixed)+1):
                    inputsAndOutputs.append("{}[{}]".format(j.name,k))
            else:
                inputsAndOutputs.append(j.name)

    file.write("NETS " + str(len(wires)+len(inputsAndOutputs))+" ; \n")

    for i in range(0,len(wires)):
        netString = " - "

        if i<len(wires)-1:
            wire = getName(f[wires[i]:wires[i+1]])
        else:
            wire = getName(f[wires[i]:len(f)])

        wireOcc = [_.start() for _ in re.finditer(wire, f)]
        tempInOut = wire.replace("!!","\\").replace("==","[").replace("@@","]")
        
        netString += tempInOut

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


    for i in range(0,len(inputsAndOutputs)):
        netString = " - "
        inOut = inputsAndOutputs[i].replace("\\","!!").replace("[","==").replace("]","@@")
        inOutOcc = [_.start() for _ in re.finditer("\({}\)".format(inOut), f)]
        tempInOut = inOut.replace("!!","\\").replace("==","[").replace("@@","]")
        
        netString += tempInOut
        netString += " ( PIN {} )".format(tempInOut)

        tempNetStrings=[]
        for j in range(0, len(inOutOcc)): #Loop on all occurances of the inOut and ignore the first one
            counter = 2
            k = inOutOcc[j]
            curInput = f[k-19+f[k-20:k].rfind("."):k]
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

def parseComponents(inputFile, file):
    statements = parseAllStatements(inputFile, ["module","wire","input","output"])

    file.write("COMPONENTS "+str(len(statements))+" ;\n")
    for cur in statements:
        file.write("-")
        file.write(cur[cur.find(" "):cur.find("(")])
        file.write(cur[0:cur.find(" ")])
        file.write(" ;\n")

    file.write("END COMPONENTS \n")

def parsePins(file,vlogModules, pinStartX, pinStartY, pinEndX, pinEndY, metalLayer, dieWidth, dieHeight):
    
    numberOfPins = calculateNumOfPins(vlogModules) 
    file.write("PINS "+str(numberOfPins)+" ;\n")
    perimeter = (2*dieWidth)+(2*dieHeight)
    spacing = int(perimeter/numberOfPins) 

    x = 0 
    y = 0
    xFlag = True
    yFlag = True

    for i in vlogModules:
        for m in i.ports:  
                if(m.data_type==""): 
                    
                    file.write("- " + m.name + " + NET " + m.name + " + DIRECTION INPUT + USE SIGNAL\n + PORT\n   + LAYER met"+str(metalLayer)+" ( "+str(pinStartX)+" "+str(pinStartY)+" ) ( "+str(pinEndX)+" "+str(pinEndY) + " )\n  + PLACED ( "+str(x)+" " +str(y) +" ) N ;\n")
                    if((x<=dieWidth)&(xFlag==True)):
                        x = x+spacing
                        
                    elif(x>dieWidth):
                        xFlag = False 
                        
                        y = y+ spacing
                        
                    elif(y>dieHeight): 
                        yFlag = False 
                        x = x - spacing
                        
                    elif((x==0)&(x==False)):
                        y = y - spacing
                        
                
                else:
                    toint = m.data_type.split(":")
                    fixed = toint[0][2:] 
                    nLoop = int(fixed)
                    for k in range(nLoop+1): 
                        file.write("- " + m.name +"["+str(k)+"]"+ " + NET " + m.name +"["+str(k)+"]"+ " + DIRECTION INPUT + USE SIGNAL\n + PORT\n   + LAYER met"+str(metalLayer)+" ( "+str(pinStartX)+" "+str(pinStartY)+" ) ( "+str(pinEndX)+" "+str(pinEndY) + " )\n  + PLACED ( "+str(x)+" " +str(y) +" ) N ;\n")
                        if((x<dieWidth)&(xFlag==True)):
                            x = x+spacing
                             
                        if(x>=dieWidth):
                            xFlag = False 
                            
                            y = y+ spacing
                        if(y>dieHeight): 
                            yFlag = False 
                            
                            x = x - spacing
                        if((x==0)&(xFlag==False)):
                            y = y - spacing
         
    #for i in vlogModules:
     #   for m in i.ports: 
      #      if(m.data_type==""): 
       #         
        #        file.write("- " + m.name + " + NET " + m.name + " + DIRECTION INPUT + USE SIGNAL\n + PORT\n   + LAYER met"+str(metalLayer)+" ( "+str(pinStartX)+" "+str(pinStartY)+" ) ( "+str(pinEndX)+" "+str(pinEndY) + " )\n  + PLACED ( "+str(x)+" " +str(y) +" ) N ;\n")

         #   else:
          #      toint = m.data_type.split(":")
           #     fixed = toint[0][2:] 
            #    nLoop = int(fixed)
             #   for k in range(nLoop+1): 

              #      file.write("- " + m.name +"["+str(k)+"]"+ " + NET " + m.name +"["+str(k)+"]"+ " + DIRECTION INPUT + USE SIGNAL\n + PORT\n   + LAYER met"+str(metalLayer)+" ( "+str(pinStartX)+" "+str(pinStartY)+" ) ( "+str(pinEndX)+" "+str(pinEndY) + " )\n  + PLACED ( "+str(x)+" " +str(y) +" ) N ;\n")
                      
    file.write("END PINS \n")   

def calcArea(inputFile):
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
    
    statements = parseAllStatements(inputFile,["module","wire","input","output"])
    totalArea = 0
    for cur in statements:
        curComponent = cur[0:cur.find(" ")]
        totalArea += macrosDimensions[curComponent][0]*macrosDimensions[curComponent][1]

    
    return totalArea

def calculateLengthWidthOfCore(inputFile, AspectRatio, coreUtilization): 
    siteWidth = parseSiteWidth()
    siteHeight = parseUnitHeight()
    area  = calcArea(inputFile) 

    coreArea = float(area/coreUtilization)
    coreWidth = float (math.sqrt(coreArea*(1/AspectRatio)))
    coreHeight = float(AspectRatio*coreWidth)
    totalSites = int(coreWidth/siteWidth)
    numberOfRows = int(coreHeight/siteHeight)


    return coreArea,coreWidth, coreHeight, totalSites, numberOfRows 

def calculateLengthWidthOfDie(inputFile,AspectRatio, dieUtilization): 
    siteWidth = parseSiteWidth()
    siteHeight = parseUnitHeight()
    area  = calcArea(inputFile) 
   
    dieArea = area/dieUtilization
    dieArea = dieArea/dieUtilization
    dieWidth = float (math.sqrt(dieArea*(1/AspectRatio)))
    dieHeight = float(AspectRatio*dieWidth)

    return dieArea,dieWidth, dieHeight

def main():
    if len(sys.argv)<2:
        print("Please, provide the input file name")
        return

    inputFile = sys.argv[1]
    

    AspectRatio = 0.5 
    coreUtilization = .70
    dieUtilization = 0.70
    marginX = 5520 
    marginYBottom = 10880

    coreArea,coreWidth, coreHeight, totalSites, numberOfRows = calculateLengthWidthOfCore(inputFile, AspectRatio, coreUtilization)
    dieArea,dieWidth, dieHeight = calculateLengthWidthOfDie(inputFile, AspectRatio, dieUtilization)
   
    #params for pins 

    #from the generated .def file as instructed 
    pinStartX = -140
    pinEndX = 140
    pinStartY = -2000 
    pinEndY =  2000
    metalLayer = 2 

    vlog_ex = vlog.VerilogExtractor()
    vlogModules = vlog_ex.extract_objects(inputFile)

    outputFile = vlogModules[0].name+".floorplan2.def"
    print(outputFile)
    
    open(outputFile, 'w').close()
    f = open(outputFile, "a")
    parseHeader(f,vlogModules)
    f.write("DIEAREA ( 0 0 )  ( " + str(int(dieWidth)) + " " + str(int(dieHeight)) +" ); \n") #To be checked later
    parseRows(f, totalSites, numberOfRows,marginYBottom,marginX)
    parseComponents(inputFile, f)
    parsePins(f,vlogModules, pinStartX, pinStartY, pinEndX, pinEndY, metalLayer, dieWidth, dieHeight)
    parseNets(inputFile, f,vlogModules)
    # f.close()
   
main()