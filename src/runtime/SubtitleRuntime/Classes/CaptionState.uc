// 同一角色的不同 HUD 共用字幕状态，不影响原有 UI 字体或界面。
class CaptionState expands Info;

var string CaptionText[64];
var float CaptionBegin[64];
var float CaptionEnd[64];
var int CaptionOrder[64];
var int NextOrder;

simulated function AddCaption(string Message, float Begin, float End)
{
    local int i;
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

simulated function float GetBegin(int i) { return CaptionBegin[i]; }
simulated function float GetEnd(int i) { return CaptionEnd[i]; }
simulated function int GetOrder(int i) { return CaptionOrder[i]; }
simulated function string GetText(int i) { return CaptionText[i]; }

defaultproperties
{
    bHidden=True
    RemoteRole=ROLE_None
}
