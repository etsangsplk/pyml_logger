import pandas as pd
import pickle
import os
import logging
import numpy as np
class Logs:
    def __init__(self):
        self.logs=[]

    def add_log(self,log):
        self.logs.append(log)

    def get_static_variables(self):
        stat_vars={}
        for l in self.logs:
            for k in l.svar:
                stat_vars[k]=1

        return stat_vars.keys()

    def get_static_variables_values(self):
        l=[]
        for log in self.logs:
            l.append(log.svar)
        return l

    def filter_on_static(self,name=None,value=None,include_missing=False):
        logs=Logs()
        for log in logs:
            if (not name in log.svar):
                if (include_missing):
                    logs.add_log(log)
            else:
                if (log.svar[name]==value):
                    logs.add_log(log)
        return logs

    def build_dataframe(self):
        result=[]
        for l in self.logs:
            df=l.to_extended_dataframe()
            result.append(df)

        result=pd.concat(result)
        return result

    def group_by(self,static_vars=None):
        _static_vars=[]
        for s in static_vars:
            _static_vars.append("_s_"+s)
        df=self.build_dataframe().groupby(_static_vars)
        return(df)









def read_logs_from_files(filenames):
    logs=Logs()
    for f in filenames:
        log=pickle.load(open(f,"rb"))
        logs.add_log(log)
    return logs

def read_logs_from_directory(directory, extension=".log"):
    logging.info("Reading logs (%s) from director %s"% (extension,directory))
    files=[]
    for file in os.listdir(directory):
        if file.endswith(extension):
            files.append(os.path.join(directory, file))
    print(files)
    logs=read_logs_from_files(files)
    logging.info("== Found %d logs"%len(logs.logs))
    return logs

def visdom_draw_average(logs,static_vars,x,ys):
    df=logs.group_by(static_vars=static_vars)

    _ys=[]
    for y in ys:
        _ys.append("_"+y)
    _x="_"+x

    series_name=[]
    for k,_ in df:
        name=""
        for i in range(len(static_vars)):
            name+=static_vars[i]+"="+str(k[i])+" "
        series_name.append(name)

    the_xs=[]
    the_ys=[]
    for k,v in df:
        for y in _ys:
            v=v[np.isfinite(df[y])]
        v=v.mean()
        the_xs.append(v[_x].values())
        the_ys.append({})
        for y in _ys:
            the_ys[-1][y]=v[y].values()

    print(the_xs)
    print(the_ys)


