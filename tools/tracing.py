import os, sys, threading, re
import linecache, logging, inspect, dis


class TraceFilter(logging.Filter):
    def filter(self, record):
        record.levelname = "TRACE"
        return True


class CallTracing(object):
    def __init__(self, patternsToTrace,
                 traceEventTypes = ["call", "line", "return", "exception", "c_call", "c_return", "c_exception"],
                 enableSystemCallTrace=False,
                 lineNumberMaxDigits=5,
                 printSourceCode=True,
                 printFuntionCallCompleteCode=True,
                 printLocalVariables=False,
                 printNameVariables=False,
                 printGlobalVariables=False,
                 printLineVariables=True,
                 printThreadName=False,
                 printFilePath=False):
        self.traceFilterObj = TraceFilter()
        self.logger = logging.getLogger(__name__)
        self.logger.addFilter(self.traceFilterObj)

        self.patternsToTrace = patternsToTrace
        self.traceEventTypes = traceEventTypes
        self.enableSystemCallTrace = enableSystemCallTrace
        self.lineNumberMaxDigits = lineNumberMaxDigits
        self.printSourceCode = printSourceCode
        self.printFuntionCallCompleteCode = printFuntionCallCompleteCode
        self.printLocalVariables = printLocalVariables
        self.printNameVariables = printNameVariables
        self.printGlobalVariables = printGlobalVariables
        self.printLineVariables = printLineVariables
        self.printThreadName = printThreadName
        self.printFilePath = printFilePath

        if printLineVariables:
            self.compiledObj = re.compile("([a-zA-Z0-9_.]*)")


    def getNextLineNumber(self,f_code,f_lineno):
        stdout = sys.stdout
        fileHandler = open(".temp","w")
        sys.stdout = fileHandler
        dis.dis(f_code)
        sys.stdout = stdout
        fileHandler.close()

        filedata = open(".temp","r").read()
        statementList = filedata.split(os.linesep+os.linesep)
        lineNumberList = []
        for statement in statementList:
            lineData = statement.split(os.linesep)[0]
            lineDataList = lineData.split(" ")
            for lineNumber in  lineDataList:
                if lineNumber != "":
                    lineNumberList.append(lineNumber)
                    break
        index = -1
        try: index = lineNumberList.index(str(f_lineno))
        except: pass
        if -1 == index:
            if f_lineno < int(lineNumberList[0]):
                return int(lineNumberList[0])
        else:
            return int(lineNumberList[ lineNumberList.index(str(f_lineno))+1 ] )


    def tracingFunction(self,currentStackFrame, eventType, eventArguments):
        if eventType in self.traceEventTypes:
            #get the complete file path
            filePath = currentStackFrame.f_code.co_filename
            try:
                folderPath, fileName = os.path.split(filePath)
            except:
                self.logger.debug("Exception happened during path=%s split" % filePath)
                folderPath = "None"
                fileName = filePath

            if self.enableSystemCallTrace is False:
                found = False
                for pattern in self.patternsToTrace:
                    result = filePath.find(pattern)
                    if result != -1:
                        found = True

                if not found:
                    return None

            #get the function name and its line number
            functionName = currentStackFrame.f_code.co_name
            lineNumber = currentStackFrame.f_lineno
            if eventType == "call": eventTypeData = "[CALL->]"
            elif eventType == "line": eventTypeData = "[-LINE-]"
            elif eventType == "return": eventTypeData = "[RETURN]"
            else: eventTypeData = "[" + eventType.upper().ljust(6," ") + "]"

            #retrieve the source code line
            sourceCodeLine = ""
            if self.printSourceCode:
                try: sourceCodeLine = linecache.getline(filePath, lineNumber).splitlines()[0]
                except: return None

            #retrieve the local, global and variables in the name space
            codeObject = currentStackFrame.f_code
            co_names = codeObject.co_names
            f_locals = currentStackFrame.f_locals
            f_globals = currentStackFrame.f_globals

            #Print THREAD name
            threadName = ""
            if self.printThreadName:
                try: threadName = "[" + threading.currentThread().getName() + "] "
                except: threadName = "[None] "

            #print complete file path
            filepath = fileName
            if self.printFilePath:
                filepath = os.path.join(folderPath, fileName)

            #create traceData log line
            traceData = threadName + eventTypeData + filepath + ":" + functionName +  "()-" + str(lineNumber).ljust(self.lineNumberMaxDigits," ")

            #A function is called (or some other code block entered)
            if eventType == "call":
                self.logger.debug(traceData + sourceCodeLine)
                if self.printFuntionCallCompleteCode:
                    nextLineNumber = lineNumber
                    try:
                        nextLineNumber = self.getNextLineNumber(codeObject,lineNumber)
                    except:
                        self.logger.error("ERROR exception happened during 'getNextLineNumber'")
                        return

                    if lineNumber is None or nextLineNumber is None:
                        return

                    if nextLineNumber != lineNumber:
                        for i in range(lineNumber+1,nextLineNumber):
                            #retrieve the next source code line
                            try:
                                 nextSourceCodeLine = linecache.getline(filePath, i).splitlines()[0]
                                 traceData = threadName + "[      ]" + filepath + ":" + functionName +  "()-" + str(i).ljust(self.lineNumberMaxDigits," ")
                                 self.logger.debug(traceData + nextSourceCodeLine)
                            except:
                                self.logger.error("ERROR exception happened during 'getline'")

            #The interpreter is about to execute a new line of code.
            elif eventType == "line":
                #Print LOCAL variables
                localVariables = ""
                if self.printLocalVariables:
                    if len(f_locals) !=0 :
                        try:
                            if "__builtins__" in f_locals.keys():
                                f_locals["__builtins__"]["copyright"] = "copyright truncated by tracing"
                                f_locals["__builtins__"]["credits"] = "credits truncated by tracing"
                            localVariables = " #LOCALS => " + str(f_locals)
                        except:
                            localVariables = " #LOCALS => None"
                #Print NAME variables
                nameVariables = ""
                f_names = {}
                if self.printNameVariables:
                    for var in co_names:
                        if var not in f_locals:
                            try: f_names[var] = f_globals[var]
                            except: pass
                    if len(f_names) !=0:
                        nameVariables = " #NAMES=> " + str(f_names)
                #Print GLOBAL variables
                globalVariables = ""
                if self.printGlobalVariables:
                    if len(f_globals) !=0 :
                        try:
                            if "__builtins__" in f_globals.keys():
                                f_globals["__builtins__"]["copyright"] = "copyright truncated by tracing"
                                f_globals["__builtins__"]["credits"] = "credits truncated by tracing"
                            globalVariables = " #GLOBALS => " + str(f_globals)
                        except:
                            globalVariables = " #GLOBALS => None"
                #Print line variable VALUES
                lineVariables = ""
                if self.printLineVariables:
                    f_lineVariables = {}
                    resultList = set(self.compiledObj.findall(sourceCodeLine))
                    for var in resultList:
                        try:
                            pyobject =  eval(var,f_globals,f_locals)
                            if hasattr(pyobject, "__call__"):
                                continue
                        except Exception, e:
                            pass
                        if var in f_locals:
                            f_lineVariables[var] = f_locals[var]
                        elif var in f_globals:
                            f_lineVariables[var] = f_globals[var]
                        else:
                            if "." in var:
                                try:
                                    varValue = eval(var,f_globals,f_locals)
                                    f_lineVariables[var] = varValue
                                except:
                                    pass
                    if len(f_lineVariables) != 0:
                        lineVariables = " #VALUES => " + str(f_lineVariables)

                self.logger.debug(traceData + sourceCodeLine + lineVariables + localVariables + nameVariables + globalVariables)

            #A function (or other code block) is about to return.
            elif eventType == "return":
                self.logger.debug(traceData + sourceCodeLine +  " #RETURN => " + str(eventArguments))
            #When an exception occurs during execution
            elif eventType == "exception":
                self.logger.debug(traceData + sourceCodeLine + " #EXCEPTION => " + str(eventArguments) )
            #A C function is about to be called. This may be an extension function or a built-in. arg is the C function object.
            elif eventType == "c_call":
                self.logger.debug(traceData + sourceCodeLine)
            #A C function has returned. arg is the C function object.
            elif eventType == "c_return":
                self.logger.debug(traceData + sourceCodeLine)
            #A C function has raised an exception. arg is the C function object.
            elif eventType == "c_exception":
                self.logger.debug(traceData + sourceCodeLine)
            else:
                print "ERROR !!!"
            return self.tracingFunction

    def start(self):
        threading.settrace(self.tracingFunction)

    def stop(self):
        threading.settrace(None)
