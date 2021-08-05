import math

class Cache:
    def __init__(self, totalsize, associativity, blocksize):
        self.totalsize = totalsize
        self.associativity = associativity
        self.blocksize = blocksize
        self.totalblocks = totalsize//blocksize
        self.totalsets = self.totalblocks//associativity
        self.arr = [[[None, 'I', '00000000',False] for i in range(associativity)] for j in range(self.totalsets)]
        self.lru = [[] for j in range(self.totalsets)]

    def GetSetNoTagNo(self, addr):
        binaddr = bin(addr)[2:][:int(-math.log2(self.blocksize))]
        binsetno = binaddr[int(-math.log2(self.totalsets)):]
        if len(binsetno)==0:
            setno = 0
        else:
            setno = int(binsetno, 2)

        bintagno = binaddr[:int(-math.log2(self.totalsets))]
        if len(bintagno)==0:
            tagno = 0
        else:
            tagno = int(bintagno, 2)
        return setno, tagno

    def CheckMiss(self, addr):
        setno, tagno = self.GetSetNoTagNo(addr)
        for blockno in range(self.associativity):
            #newly added
            if (self.arr[setno][blockno][0]==tagno)  and (self.arr[setno][blockno][3] is True):
                self.ChangeLRU(blockno, setno)  
                return self.arr[setno][blockno][1], self.arr[setno][blockno][2], self.arr[setno][blockno][3]#False #hit


        return 'I','00000000',False #True #miss
    def CheckMiss_L1(self, addr):
        setno, tagno = self.GetSetNoTagNo(addr)
        for blockno in range(self.associativity):
            if (self.arr[setno][blockno][0]==tagno) and (self.arr[setno][blockno][1]!='I'):

                self.ChangeLRU(blockno, setno)
                return self.arr[setno][blockno][1], self.arr[setno][blockno][2], self.arr[setno][blockno][3]#False #hit

        return 'I','00000000',False #True #miss

    def ChangeLRU(self, blockno, setno):
        for i in range(len(self.lru[setno])):
            if self.lru[setno][i] == blockno:
                self.lru[setno].pop(i)
                break
        self.lru[setno].append(blockno)


    def Evict(self, blkaddr):
        setno, tagno = self.GetSetNoTagNo(blkaddr)
        for blockno in range(self.associativity):
            if self.arr[setno][blockno][0]==tagno and self.arr[setno][blockno][3] is True:
                self.arr[setno][blockno][1] = 'I'
                self.arr[setno][blockno][3] = False
                
                for i in range(len(self.lru[setno])):
                    if self.lru[setno][i] == blockno:
                        self.lru[setno].pop(i)
                        break


    def Replacement(self, addr, n):
        setno, tagno = self.GetSetNoTagNo(addr)
        for blockno in range(self.associativity):
            if (self.arr[setno][blockno][1]=='I' and self.arr[setno][blockno][3] is False):
                self.arr[setno][blockno][0] = tagno
                self.arr[setno][blockno][1] = 'I'
                self.arr[setno][blockno][2]='00000000'
                self.arr[setno][blockno][3]=True
                self.ChangeLRU(blockno, setno)
                return None, None, None

        evict = self.lru[setno].pop(0) # evict has block number

        evicttag = self.arr[setno][evict][0]
        stateevict=self.arr[setno][evict][1]
        bitvect=self.arr[setno][evict][2]
        binsetno = bin(setno)[2:].zfill(int(math.log2(self.totalsets)))
        blkaddr = int(bin(evicttag)[2:] + binsetno + '0'*int(math.log2(self.blocksize)),2)

        self.arr[setno][evict][0] = tagno
        self.arr[setno][evict][1] = 'I'
        self.arr[setno][evict][2]='00000000'
        self.arr[setno][evict][3]=True
        self.lru[setno].append(evict)

        return blkaddr, stateevict, bitvect

    #newly added method
    def modify_state(self, addr,state):
        setno, tagno = self.GetSetNoTagNo(addr)
        for blockno in range(self.associativity):
            if (self.arr[setno][blockno][0] == tagno) : # & (self.arr[setno][blockno][1] != 'I')added I state check here to make sure it was not invalidated by some other core
                self.arr[setno][blockno][1]=state

    def find_bank_id(self,addr):
        setno, tagno = self.GetSetNoTagNo(addr)
        bankid=setno & 7
        return bankid

    def modify_bitvector(self,addr,coreid,state):
        setno, tagno = self.GetSetNoTagNo(addr)
        for blockno in range(self.associativity):
            if (self.arr[setno][blockno][0] == tagno):
                self.arr[setno][blockno][1] = state
                bitvector=str(self.arr[setno][blockno][2])
                if state=='M' or state=='E':
                    bitvector='00000000'
                bitvector_new=bitvector[:coreid]+'1'+bitvector[coreid+1:] # need to check whether this works by debugging
                self.arr[setno][blockno][2]=bitvector_new

    def change_bitvector_replacement(self,addr,coreid):
        setno, tagno = self.GetSetNoTagNo(addr)
        for blockno in range(self.associativity):
            if (self.arr[setno][blockno][0] == tagno):
                if self.arr[setno][blockno][1]=='M' or self.arr[setno][blockno][1]=='E':
                    self.arr[setno][blockno][1]='I'
                    bitvector_new = '00000000'
                elif self.arr[setno][blockno][1]=='S':
                    bitvector=str(self.arr[setno][blockno][2])
                    bitvector_new=bitvector[:coreid]+'0'+bitvector[coreid+1:] # need to check whether this works by debugging
                else:
                    bitvector_new=str(self.arr[setno][blockno][2])
                    
                self.arr[setno][blockno][2]=bitvector_new

    def get_blockno(self, addr):
        return bin(addr)[2:][:int(-math.log2(self.blocksize))]
        
        


if __name__ == "__main__":
    print('Write debug code here')