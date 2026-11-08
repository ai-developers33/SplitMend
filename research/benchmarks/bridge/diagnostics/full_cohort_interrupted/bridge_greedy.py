"""Explicit multi-group/quarantine heuristic extensions for enrolment records.

Search over offering assignments. Given offerings, choose each student's
lowest-cost retained partition, quarantining incompatible enrolments. Greedily
trim upper bounds, then use student-coordinate improvements. No MILP calls.
"""
import time
import numpy as np


class BridgeModel:
    def __init__(self, frame, original, locked, policy):
        self.frame = frame
        self.courses = sorted(frame.offering.unique())
        self.students = sorted(frame.student.unique())
        self.labels = sorted(frame.label.unique())
        ci = {x:i for i,x in enumerate(self.courses)}
        si = {x:i for i,x in enumerate(self.students)}
        li = {x:i for i,x in enumerate(self.labels)}
        self.c = np.array([ci[x] for x in frame.offering])
        self.s = np.array([si[x] for x in frame.student])
        self.y = np.array([li[x] for x in frame.label])
        self.original = np.asarray(original, dtype=np.int8)
        self.locked = np.asarray(locked, dtype=bool)
        self.n = len(frame)
        self.ns = len(si)
        self.nl = len(li)
        self.qcost = policy.quarantine_cost
        self.fixed_students = np.full(self.ns, -1, dtype=np.int8)
        self.fixed_students[self.s[self.locked]] = self.original[self.locked]
        self.initial_courses = np.full(len(ci), -1, dtype=np.int8)
        for i in range(len(ci)):
            parts = set(self.original[self.c == i])
            assert len(parts) == 1
            self.initial_courses[i] = parts.pop()
        self.free_courses = np.flatnonzero(self.initial_courses != 2)
        self.lo = np.zeros((3,self.nl+1), dtype=np.int64)
        self.hi = np.full((3,self.nl+1), self.n, dtype=np.int64)
        for p, name in enumerate(policy.partitions):
            self.lo[p,0], self.hi[p,0] = policy.size_bounds[name]
            for j,label in enumerate(self.labels):
                self.lo[p,j+1], self.hi[p,j+1] = policy.label_bounds[label][name]

    def counts(self, destinations):
        keep = destinations < 3
        counts = np.bincount(destinations[keep]*self.nl+self.y[keep], minlength=3*self.nl).reshape(3,self.nl)
        return np.column_stack([counts.sum(axis=1), counts])

    def costs(self, destinations):
        return np.where(destinations == self.original, 0,
                        np.where(destinations == 3, self.qcost, 1))

    def violation(self, counts):
        return np.maximum(self.lo-counts,0).sum(axis=(-2,-1)) + np.maximum(counts-self.hi,0).sum(axis=(-2,-1))

    def trim_upper(self, dest):
        """Remove cheapest eligible rows, never a lock or below a label minimum."""
        dest = dest.copy()
        counts = self.counts(dest)
        loss = self.qcost - self.costs(dest)
        for p in [0,1]:
            for j in range(self.nl):
                excess = max(0, int(counts[p,j+1]-self.hi[p,j+1]))
                if not excess: continue
                rows = np.flatnonzero((dest == p)&(self.y == j)&~self.locked)
                rows = rows[np.lexsort((rows,loss[rows]))][:excess]
                dest[rows] = 3
                counts[p,j+1] -= len(rows)
                counts[p,0] -= len(rows)
            excess = max(0, int(counts[p,0]-self.hi[p,0]))
            if not excess: continue
            rows = np.flatnonzero((dest == p)&~self.locked)
            rows = rows[np.lexsort((rows,loss[rows]))]
            for r in rows:
                j = self.y[r]
                if counts[p,j+1] <= self.lo[p,j+1]: continue
                dest[r] = 3
                counts[p,j+1] -= 1
                counts[p,0] -= 1
                excess -= 1
                if not excess: break
        return dest

    def decode(self, course_sides):
        requested = course_sides[self.c]
        gains = np.bincount(self.s*3+requested,
                weights=self.qcost-(requested != self.original), minlength=self.ns*3).reshape(self.ns,3)
        student_sides = gains.argmax(axis=1)
        fixed = self.fixed_students >= 0
        student_sides[fixed] = self.fixed_students[fixed]
        dest = np.where(requested == student_sides[self.s], requested, 3).astype(np.int8)
        dest = self.trim_upper(dest)
        return dest

    def student_polish(self, course_sides, dest, deadline, cost_aware=True):
        """Full single-student neighborhood, including restoration of quarantine.

        A candidate replaces all that student's rows by the best assignment
        consistent with one chosen partition and the current offering colors.
        Strict violation reduction, then strict feasible objective reduction.
        """
        requested = course_sides[self.c]
        possible = []
        for side in [0,1]:
            keep = requested == side
            by = np.bincount(self.s[keep]*self.nl+self.y[keep],minlength=self.ns*self.nl).reshape(self.ns,self.nl)
            stats = np.zeros((self.ns,3,self.nl+1),dtype=np.int64)
            stats[:,side,1:] = by
            stats[:,side,0] = by.sum(axis=1)
            row_cost = np.where(keep, requested != self.original, self.qcost)
            costs = np.bincount(self.s,weights=row_cost,minlength=self.ns).astype(np.int64)
            possible.append((stats,costs))
        free = self.fixed_students < 0
        steps = 0
        while time.perf_counter() < deadline and steps < 10000:
            counts = self.counts(dest)
            violation = int(self.violation(counts))
            keep = dest < 3
            cur = np.bincount((self.s[keep]*3+dest[keep])*self.nl+self.y[keep],
                             minlength=self.ns*3*self.nl).reshape(self.ns,3,self.nl)
            current_stats = np.concatenate([cur.sum(axis=2,keepdims=True),cur],axis=2)
            current_cost = np.bincount(self.s,weights=self.costs(dest),minlength=self.ns).astype(np.int64)
            best = None
            for side,(stats,cost) in enumerate(possible):
                violations = self.violation(counts + stats - current_stats)
                increments = cost - current_cost
                eligible = np.flatnonzero(free & ((violations < violation) if violation else ((violations == 0)&(increments < 0))))
                if not len(eligible): continue
                if violation:
                    improve = violation-violations[eligible]
                    primary = increments[eligible]/improve if cost_aware else violations[eligible]
                    order = np.lexsort((eligible,increments[eligible],violations[eligible],primary))
                    i = eligible[order[0]]
                    key = (float(primary[order[0]]),int(violations[i]),int(increments[i]),int(i),side)
                else:
                    i = eligible[np.lexsort((eligible,increments[eligible]))[0]]
                    key = (int(increments[i]),int(i),side)
                if best is None or key < best[0]: best = (key,int(i),side)
            if best is None: break
            _,student,side = best
            rows = self.s == student
            dest[rows] = np.where(requested[rows] == side, side, 3)
            steps += 1
        return dest,steps


def run(model, method, budget=60):
    start = time.perf_counter()
    deadline = start + budget
    course_sides = model.initial_courses.copy()
    dest = model.decode(course_sides)
    steps = evaluations = student_steps = 0
    reason = 'budget'
    while time.perf_counter() < deadline:
        before = int(model.violation(model.counts(dest)))
        cost = int(model.costs(dest).sum())
        moves = [(int(i),) for i in model.free_courses]
        if method == 'all_pair_bridge' or (method == 'cost_aware_bridge_exchanges' and before == 0):
            moves += [(int(i),int(j)) for k,i in enumerate(model.free_courses) for j in model.free_courses[k+1:]
                      if method == 'all_pair_bridge' or course_sides[i] != course_sides[j]]
        best = None
        for move in moves:
            if time.perf_counter() >= deadline: break
            candidate_courses = course_sides.copy()
            candidate_courses[list(move)] = 1-candidate_courses[list(move)]
            candidate = model.decode(candidate_courses)
            v = int(model.violation(model.counts(candidate)))
            c = int(model.costs(candidate).sum())
            evaluations += 1
            if before:
                if v >= before: continue
                primary = v if method == 'violation_first_bridge' else (c-cost)/(before-v)
                key = (float(primary),v,c,move)
            else:
                if method == 'violation_first_bridge' or v != 0 or c >= cost: continue
                key = (c,move)
            if best is None or key < best[0]: best = (key,candidate_courses,candidate)
        if best is not None:
            _,course_sides,dest = best
            steps += 1
            continue
        if time.perf_counter() >= deadline: break
        old_dest = dest.copy()
        dest,ns = model.student_polish(course_sides,dest,deadline,method != 'violation_first_bridge')
        student_steps += ns
        if not np.array_equal(dest,old_dest):
            # A violation-first method stops once feasibility has been reached.
            if method == 'violation_first_bridge' and model.violation(model.counts(dest)) == 0:
                reason = 'feasible';break
            continue
        reason = 'local_neighborhood_exhausted'
        break
    return dest,{'search_seconds':time.perf_counter()-start,'course_moves':steps,
                 'student_moves':student_steps,'candidates_evaluated':evaluations,
                 'stop_reason':reason,'remaining_count_violation':int(model.violation(model.counts(dest)))}
