from datetime import datetime,date,time
import os.path
import pickle
import pandas as pd
import numpy as np

class Log:
    '''
    A log is composed of:
        - static key,value pairs (for example: hyper parameters of the experiment)
        - set of key,value pairs at each iteration

    Typical use is:
        log.add_static_value("learning_rate",0.01)

        for t in range(T):
            perf=evaluate_model()
            log.new_iteration()
            log.add_dynamic_value("perf",perf)
            log.add_dynamic_value("iteration",t)
    '''
    def __init__(self,use_tensorboard=False):
        self.svar={}
        self.dvar=[]
        self.t=-1
        self.scopes=[]
        self.file=None


    def add_static_value(self,key,value):
        self.svar[key]=value

    def new_iteration(self):
        if (self.t>=0):
            print(self.dvar[self.t])

        self.t=self.t+1
        self.dvar.append({})
        self.scopes = []

    def push_scope(self, name):
        self.scopes.append(name)

    def pop_scope(self):
        return self.scopes.pop()

    def _get_dtable(self,scope,t):
        tt=self.dvar[t]
        for s in scope:
            tt=tt[s]
        return tt

    def add_dynamic_value(self,key,value):
        tt=self.dvar[self.t]
        for s in self.scopes:
            if (not s in tt):
                tt[s]={}
            tt=tt[s]

        tt[key]=value


    def get_last_dynamic_value(self,key):
        key=".".join(self.scopes)+key
        return self.dvar[self.t][key]

    def get_column(self,key):
        c=[]
        for d in self.dvar:
            c.append(d[key])
        return c

    def print_static(self):
        print("===== STATIC VARIABLES =========")
        for i in self.svar:
            print(str(i)+" = "+str(self.svar[i]))

    def _generate_columns_names(self):
        columns={}
        scope=[]
        for t in range(self.t):
            tt=self.dvar[t]
            cc=self._generate_columns_names_from_dict(tt,scope)
            for kk in cc.keys():
                columns[kk]=1
        return columns

    def _generate_columns_names_from_dict(self,d,scope):
        columns={}
        for k in d.keys():
            if (isinstance(d[k],dict)):
                scope.append(k)
                cc=self._generate_columns_names_from_dict(d[k],scope)
                for kk in cc.keys():
                    columns[kk]=1
                scope.pop()
            else:
                columns[".".join(scope)+"."+k]=1

        return columns

    def get_scoped_value(self,t,name):
        scope=name.split(".")
        tt=self.dvar[t]
        for s in scope:
            if (not s in tt):
                return None
            tt=tt[s]
        return tt

    def save(self,filename=None,directory=None):
        if (directory is None):
            directory="logs"

        if (filename is None):
            filename=str(datetime.now()).replace(" ","_")+".log"
            while(os.path.isfile(directory+"/"+filename)):
                filename = str(datetime.now()).replace(" ", "_")+".log"
        print("Saving in file is " + directory+"/"+filename)
        pickle.dump( self, open( directory+"/"+filename, "wb" ) )

    def get_static_values(self):
        return self.svar

    def to_array(self):
        '''
        Transforms the dynamic values to an array
        '''
        names = self._generate_columns_names()
        names["_iteration"] = 1

        retour = []
        cn = []
        for l in names:
            cn.append(l)
        retour.append(cn)

        for t in range(len(self.dvar)):
            cn = []
            for l in names:
                if (l == "_iteration"):
                    cn.append(t)
                else:
                    v = self.get_scoped_value(t, l)
                    cn.append(v)
            retour.append(cn)
        return retour



    def to_extended_array(self):
        '''
        Transforms the dynamic+static  values to an array
        '''
        names = self._generate_columns_names()
        names["_iteration"] = 1

        for k in self.svar:
            names["_s_"+k]=1

        retour = []
        cn = []
        for l in names:
            cn.append(l)
        retour.append(cn)

        for t in range(len(self.dvar)):
            cn=[]
            for l in names:
                if (l.startswith('_s_')):
                    cn.append(self.svar[l[3:]])
                elif (l == "_iteration"):
                    cn.append(t)
                else:
                    v = self.get_scoped_value(t, l)
                    cn.append(v)
            retour.append(cn)
        return retour

    def to_dataframe(self):
        a = self.to_array()
        return pd.DataFrame(data=a[1:], columns=a[0])


    def to_extended_dataframe(self):
        a = self.to_extended_array()
        return pd.DataFrame(data=a[1:], columns=a[0])


def logs_to_dataframe(filenames):
    print("Loading %d files and building Dataframe" % len(filenames))
    arrays=[]
    for f in filenames:
        log=pickle.load(open(f,"rb"))
        arrays.append(log.to_extended_array())

    #Building the set of all columns + index per log
    indexes=[]
    all_columns={}
    for i in range(len(arrays)):
        index={}
        columns_names=arrays[i][0]
        for j in range(len(columns_names)):
            index[columns_names[j]]=j
            all_columns[columns_names[j]]=1

        indexes.append(index)

    retour=[]
    all_names=["_log_idx","_log_file"]
    for a in all_columns:
        all_names.append(a)

    for i in range(len(arrays)):
        arr=arrays[i]
        filename=filenames[i]

        for rt in range(len(arr)-1):
            t=rt+1
            line=arr[t]

            new_line=[]
            for idx_c in range(len(all_names)):
                new_line.append(None)
            for idx_c in range(len(all_names)):
                column_name=all_names[idx_c]

                if (column_name == "_log_file"):
                    new_line[idx_c] = filename
                elif (column_name == "_log_idx"):
                    new_line[idx_c] = i
                elif (column_name in indexes[i]):
                    idx = indexes[i][column_name]
                    new_line[idx_c] = arr[t][idx]

            retour.append(new_line)

    return pd.DataFrame(data=retour,columns=all_names)


class VisdomLog(Log):

    def __init__(self,env='main',update_every=10):
        import visdom

        Log.__init__(self)
        self.vis=visdom.Visdom(env=env)
        self.observer_line=[]
        self.update_every=update_every
        self.last_update=0

    def observe_as_line(self,column_names,opts={}):
        self.observer_line.append((None,column_names,opts))

    def new_iteration(self):
        Log.new_iteration(self)

        if (len(self.dvar)<2):
            return
        if ((len(self.dvar)-1)%self.update_every!=0):
            return
        #Update lines
        pos=0
        for pos in range(len(self.observer_line)):
            o=self.observer_line[pos]
            column_names=o[1]
            win=o[0]
            opts=o[2]
            val=self._get_np_values(column_names,_from=self.last_update)
            if(not val is None):
                X=val[0]
                Y=val[1]
                if (win is None):
                    opts_ = {}
                    opts_["legend"] = column_names
                    for k in opts:
                        opts_[k] = opts[k]
                    self.observer_line[pos]=(self.vis.line(X=X, Y=Y, opts=opts_),o[1],o[2])
                else:
                    self.vis.updateTrace(X=X,Y=Y,win=win)
            pos+=1
        self.last_update+=self.update_every

    def _get_np_values(self, column_names,_from=0):
        Y=[]
        X=[]
        _to=len(self.dvar)
        if (len(self.dvar[-1])==0):
            _to-=1

        for t in range(_from, _to):
            _val = []
            _x=[]
            all_none=True
            for c in column_names:
                v=self.get_scoped_value(t, c)
                if (not v is None):
                    all_none=False
                else:
                    v=0
                _val.append(v)
                _x.append(t)

            if (not all_none):
                Y.append(_val)
                X.append(_x)
        if (len(X)==0):
            return None
        if (len(Y[0])==1):
            Y=Y[0]
            X=X[0]
        return (np.array(X),np.array(Y))
