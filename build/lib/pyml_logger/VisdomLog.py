
import visdom


class VisdomLog(pyml_logger.Log):

    def __init__(self,env='main'):
        Log.__init__(self)
        self.vis=visdom.Visdom(env=env)
        self.observer_line=[]

    def observe_as_line(self,column_names,opts={}):
        self.observer_line.append((None,column_names,opts))

    def new_iteration(self):
        Log.new_iteration(self)


        for o in self.observer_line:
            column_names=o[1]
            win=o[0]
            opts=o[2]
            (X,Y)=self._get_values(self,column_names)

            if (win is None):
                opts_ = {}
                opts_["legend"] = column_names
                for k in opts:
                    opts_[k] = opts[k]
                o[0]=self.vis.line(X=X, Y=Y, opts=opts_)
            else:
                self.vis.updateTrace(X=X,Y=Y,win=win)

    def _get_values(self, column_names):
        if (len(self.dvar) <= 1):
            return None

        if (self.vis is None):
            self.vis = visdom.Visdom()

        r = []
        X = []
        for t in range(len(self.dvar)):
            rr = []
            for c in column_names:
                rr.append(self.get_scoped_value(t, c))
            r.append(rr)
            X.append(t)
        return (np.array(X),np.array(r))
