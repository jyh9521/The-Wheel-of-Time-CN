// 同一角色的不同 HUD 共用字幕状态，不影响原有 UI 字体或界面。
class CaptionState expands Info;

var string CaptionText[64];
var float CaptionBegin[64];
var float CaptionEnd[64];
var int CaptionOrder[64];
var int NextOrder;

simulated function AddCaption(string Message, float Begin, float End)
{
    local int i, MatchIndex;
    if (Message == "" || End <= Begin || End <= Level.TimeSeconds) return;
    MatchIndex = -1;
    // 同文且时间区间重叠的回调合并；不同对白和不重叠的重播保留。
    for (i=0; i<64; i++)
    {
        if (CaptionEnd[i] > Level.TimeSeconds && CaptionText[i] == Message
            && CaptionBegin[i] < End && Begin < CaptionEnd[i])
        {
            if (MatchIndex < 0) MatchIndex = i;
            else
            {
                CaptionBegin[MatchIndex] = FMin(CaptionBegin[MatchIndex], CaptionBegin[i]);
                CaptionEnd[MatchIndex] = FMax(CaptionEnd[MatchIndex], CaptionEnd[i]);
                CaptionEnd[i] = 0;
            }
        }
    }
    if (MatchIndex >= 0)
    {
        CaptionBegin[MatchIndex] = FMin(CaptionBegin[MatchIndex], Begin);
        CaptionEnd[MatchIndex] = FMax(CaptionEnd[MatchIndex], End);
        return;
    }
    for (i=0; i<64; i++)
    {
        if (CaptionEnd[i] <= Level.TimeSeconds)
        {
            CaptionText[i] = Message;
            CaptionBegin[i] = Begin;
            CaptionEnd[i] = End;
            CaptionOrder[i] = NextOrder;
            NextOrder++;
            return;
        }
    }
    Log("SubtitleRuntime: caption capacity reached");
}

// 兼容旧存档中的重复槽位，只绘制最早入队的一份活动字幕。
simulated function bool IsDuplicate(int Index)
{
    local int i;
    for (i=0; i<64; i++)
        if (i != Index && CaptionText[i] == CaptionText[Index]
            && CaptionBegin[i] <= Level.TimeSeconds && CaptionEnd[i] > Level.TimeSeconds
            && CaptionOrder[i] < CaptionOrder[Index]) return true;
    return false;
}

simulated function float GetBegin(int i) { return CaptionBegin[i]; }
simulated function float GetEnd(int i) { return CaptionEnd[i]; }
simulated function int GetOrder(int i) { return CaptionOrder[i]; }
simulated function string GetText(int i) { return CaptionText[i]; }

defaultproperties
{
    bHidden=True
    RemoteRole=ROLE_None
}
