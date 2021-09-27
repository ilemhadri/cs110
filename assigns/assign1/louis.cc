vector<int> neighbors(int u)
{
    if (u < 0)
    {
        // u is movie
        return movieNeighbors(-u);
    }
    else
    {
        // u is actor
        auto ans = actorNeighbors(u);
        for (auto &x : ans)
            x = -x;
        return ans;
    }
}

vector<int> bfs(int start, int end)
{
    vector<int> Q = {start};
    map<int, int> backtracking;
    backtracking[start] = start;

    bool stop = false;
    while (!Q.empty() and !stop)
    {
        vector<int> newQ;
        for (auto u : Q)
        {
            for (auto v : neighbors(u))
            {
                if (backtracking.find(v) == backtracking.end())
                    newQ.push_back(v), backtracking[v] = u;
                if (v == end)
                {
                    stop = true;
                    break;
                }
            }
            if (stop)
                break;
        }
    }
    if (backtracking.find(end) == backtracking.end())
        // didn't find end
        assert(false);
    vector<int> path = {end};
    int cur = end;
    while (cur != start)
    {
        cur = backtracking[cur];
        path.push_back(cur);
    }
    return cur;
    // post processing because movies are < 0
}
