/*BEGIN_LEGAL 
Intel Open Source License 

Copyright (c) 2002-2018 Intel Corporation. All rights reserved.
 
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.  Redistributions
in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.  Neither the name of
the Intel Corporation nor the names of its contributors may be used to
endorse or promote products derived from this software without
specific prior written permission.
 
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
END_LEGAL */
/*
 *  This file contains an ISA-portable PIN tool for tracing memory accesses.
 */
using namespace std;
#include <iostream>
#include <fstream>
#include <stdio.h>
#include "pin.H"

ofstream OutFile;
FILE * trace;
PIN_LOCK pinLock;
unsigned long long int line_count=0;
unsigned long long int global_count=0;


KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool",
    "o", "addrtrace_prog.out", "specify output file name");
//print memory accesses for each thread
VOID address_sequence(THREADID tid,uint64_t addr_int,UINT32 memopSize,bool flag)
{
	int cacheblock=64;
	uint64_t lastbyte=((addr_int/cacheblock)+1)*cacheblock;
	uint64_t l_memopsize = (uint64_t)memopSize;
	uint64_t l_memopsize_temp = l_memopsize;
	uint64_t temp_addr_int=addr_int;
	int jump=8;
	char opcode='R';
	if(flag)
	{
		opcode='W';
	}
	
	//int stride_cur=8;
	//fprintf(trace, "%d %lu\n", tid, addr_int);
	fprintf(trace, "%d %c %lu %llu\n", tid,opcode,addr_int+jump,global_count);
	global_count+=1;
	fflush(trace);
	line_count++;
	//fprintf(stdout, "thread begin %d and memopsize is  %lu and addr is %lu\n",tid,l_memopsize,addr_int);
    	//fflush(stdout);
	while(l_memopsize>1)
	{	
		
		if(addr_int+jump<lastbyte && addr_int+jump<=temp_addr_int+l_memopsize_temp)
		{
			l_memopsize-=jump;
			if(l_memopsize >0)
			{
			line_count++;
			fprintf(trace, "%d %c %lu %llu\n", tid,opcode,addr_int+jump,global_count);
			global_count+=1;
			fflush(trace);
			addr_int=addr_int+jump;
			jump=8;
			if(addr_int >lastbyte)
			lastbyte+=cacheblock;
			//stride_cur=8;
			}
			
		}
		else if(addr_int+jump==lastbyte && addr_int+jump<=temp_addr_int+l_memopsize_temp)
		{
			l_memopsize-=jump;
			if(l_memopsize >0)
			{
			line_count++;
			fprintf(trace, "%d %c %lu %llu\n", tid,opcode,addr_int+jump,global_count);
			global_count+=1;
			//fprintf(trace, "%d %lu\n", tid, addr_int+jump);
			fflush(trace);
			lastbyte+=cacheblock;
			addr_int=addr_int+jump;
			
			jump=8;
			}
			
			
		}
		else if(addr_int+jump>lastbyte ||addr_int+jump>temp_addr_int+l_memopsize_temp)
		{
		//fprintf(stdout, "thread begin %d and memopsize curr is  %lu and memopsize initial is %lu and addr is %lu and jump is %d and temp_addr is %lu and last byte is %lu\n",tid,l_memopsize,l_memopsize_temp,addr_int,jump,temp_addr_int,lastbyte);
    	        //fflush(stdout);
		if(jump>1)
		{
			while((addr_int+jump>temp_addr_int+l_memopsize_temp && jump>1)||(addr_int+jump>lastbyte && jump>1))
			{
				jump-=(jump/2);
				//fprintf(stdout, "Inside while thread begin %d and memopsize curr is  %lu and memopsize initial is %lu and addr is %lu and jump is %d and temp_addr is %lu and last byte is %lu\n",tid,l_memopsize,l_memopsize_temp,addr_int,jump,temp_addr_int,lastbyte);
    	       // fflush(stdout);
			}
		}
		else
		{
		break;
		}
		
		}
	}

}

// Print a memory read record
VOID RecordMemRead(VOID * ip, VOID * addr,THREADID tid,UINT32 memopSize)
{
	
	PIN_GetLock(&pinLock, tid+1);
	uint64_t addr_int = reinterpret_cast<uint64_t>(addr);
	address_sequence(tid,addr_int,memopSize,0);	
	PIN_ReleaseLock(&pinLock);
    	//fprintf(trace,"%p: R %p\n", ip, addr);
}

// Print a memory write record
VOID RecordMemWrite(VOID * ip, VOID * addr,THREADID tid,UINT32 memopSize)
{
	PIN_GetLock(&pinLock, tid+1);
	uint64_t addr_int = reinterpret_cast<uint64_t>(addr);
	address_sequence(tid,addr_int,memopSize,1);	
	PIN_ReleaseLock(&pinLock);
    //fprintf(trace,"%p: W %p\n", ip, addr);
}
VOID ThreadStart(THREADID tid, CONTEXT *ctxt, INT32 flags, VOID *v)
{
    PIN_GetLock(&pinLock, tid+1);
    fprintf(stdout, "thread begin %d\n",tid);
    fflush(stdout);
    PIN_ReleaseLock(&pinLock);
}
VOID ThreadFini(THREADID tid, const CONTEXT *ctxt, INT32 code, VOID *v)
{
    PIN_GetLock(&pinLock, tid+1);
    fprintf(stdout, "thread end %d code %d\n",tid, code);
    fflush(stdout);
    PIN_ReleaseLock(&pinLock);
}
// Is called for every instruction and instruments reads and writes
VOID Instruction(INS ins, VOID *v)
{
    // Instruments memory accesses using a predicated call, i.e.
    // the instrumentation is called iff the instruction will actually be executed.
    //
    // On the IA-32 and Intel(R) 64 architectures conditional moves and REP 
    // prefixed instructions appear as predicated instructions in Pin.
    UINT32 memOperands = INS_MemoryOperandCount(ins);

    // Iterate over each memory operand of the instruction.
    for (UINT32 memOp = 0; memOp < memOperands; memOp++)
    {
    UINT32 memopSize = INS_MemoryOperandSize(ins, memOp);
    	
        if (INS_MemoryOperandIsRead(ins, memOp))
        {
        
            INS_InsertPredicatedCall(
                ins, IPOINT_BEFORE, (AFUNPTR)RecordMemRead,
                IARG_INST_PTR,
                IARG_MEMORYOP_EA, memOp,
                IARG_THREAD_ID,
                IARG_UINT32, memopSize,
                IARG_END);
        }
        // Note that in some architectures a single memory operand can be 
        // both read and written (for instance incl (%eax) on IA-32)
        // In that case we instrument it once for read and once for write.
        if (INS_MemoryOperandIsWritten(ins, memOp))
        {
        //UINT32 memopSize = INS_MemoryOperandSize(ins, memOp);
            INS_InsertPredicatedCall(
                ins, IPOINT_BEFORE, (AFUNPTR)RecordMemWrite,
                IARG_INST_PTR,
                IARG_MEMORYOP_EA, memOp,
                IARG_THREAD_ID,
                IARG_UINT32, memopSize,
                IARG_END);
        }
    }
}

VOID Fini(INT32 code, VOID *v)
{
    fprintf(stdout, "The total address count is  %llu\n",line_count);
    fflush(stdout);
    fprintf(trace, "#eof\n");
    fclose(trace);
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */
   
INT32 Usage()
{
    PIN_ERROR( "This Pintool prints a trace of memory addresses\n" 
              + KNOB_BASE::StringKnobSummary() + "\n");
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char *argv[])
{
   if (PIN_Init(argc, argv)) return Usage();
    
    trace = fopen(KnobOutputFile.Value().c_str(), "w");
    PIN_InitLock(&pinLock);

    

    INS_AddInstrumentFunction(Instruction, 0);
    
    PIN_AddThreadStartFunction(ThreadStart, 0);
    PIN_AddThreadFiniFunction(ThreadFini, 0);

    PIN_AddFiniFunction(Fini, 0);

    // Never returns
    PIN_StartProgram();
    
    return 0;
}
