// 字幕专用层：其他消息继续由原始 MainHUD 绘制。
class SubtitleHUD expands MainHUD;

var string CaptionText[64];
var float CaptionBegin[64];
var float CaptionEnd[64];
var int CaptionOrder[64];
var int NextOrder;
var localized string IntroText;
var localized string CueText[16];
var float CueBegin[16];
var float CueEnd[16];
var int CueCount;
var Font SubtitleFont;

simulated function LoadCaptionText()
{
    local int i;
    IntroText=Localize("SubtitleHUD","IntroText","SubtitleRuntime",true);
    for (i=0; i<CueCount; i++)
        CueText[i]=Localize("SubtitleHUD","CueText[" $ i $ "]","SubtitleRuntime",true);
}

simulated event PostBeginPlay()
{
    Super.PostBeginPlay();
    LoadCaptionText();
}

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
    // 队列满时保留正在播放的字幕，不覆盖旧句。
    Log("SubtitleRuntime: caption capacity reached");
}

simulated function AddSubtitleMessage(string Message, optional float Duration, optional bool bEcho)
{
    local int i;
    while (Len(Message)>0 && Right(Message,1)==" ") Message=Left(Message,Len(Message)-1);
    if (Message == "") return;
    if (IntroText == "") LoadCaptionText();
    if (IntroText != "" && Left(Message, Len(IntroText)) == IntroText)
    {
        for (i=0; i<CueCount; i++)
            AddCaption(CueText[i], Level.TimeSeconds + CueBegin[i], Level.TimeSeconds + CueEnd[i]);
    }
    else
    {
        if (Duration <= 0) Duration = SubtitleMessageDuration;
        AddCaption(Message, Level.TimeSeconds, Level.TimeSeconds + Duration);
    }
    if (bEcho && PlayerPawn(Owner) != None)
        PlayerPawn(Owner).Player.Console.Message(None, Message, 'Message');
}

simulated function DrawMessages(Canvas C, float DeltaTime)
{
    local int i, j, LastOrder, BestOrder, BestIndex;
    local float X, Y, LineX, LineY, LineHeight, OldOrgX, OldOrgY, OldClipX, OldClipY;
    local Font OldFont;
    local bool OldCenter;
    local byte OldStyle;
    local color OldColor;

    // 原字幕单槽保持空，手部、中心、通用提示沿用原始路径和字号。
    SubtitleMessage.LifeSpan = 0;
    Super.DrawMessages(C, DeltaTime);
    if (SubtitleMessageIntensity == 0) return;
    if (SubtitleFont == None)
        SubtitleFont = Font(DynamicLoadObject("WOT.SubtitleFont", class'Font'));
    if (SubtitleFont == None) return;
    OldFont=C.Font; OldCenter=C.bCenter; OldStyle=C.Style; OldColor=C.DrawColor;
    OldOrgX=C.OrgX; OldOrgY=C.OrgY; OldClipX=C.ClipX; OldClipY=C.ClipY;
    C.SetFont(SubtitleFont);
    C.Style=ERenderStyle.STY_Translucent;
    C.DrawColor.R=SubtitleMessageIntensity;
    C.DrawColor.G=SubtitleMessageIntensity;
    C.DrawColor.B=SubtitleMessageIntensity;
    C.OrgX=C.SizeX/10; C.ClipX=8*C.SizeX/10;
    C.OrgY=24; C.ClipY=C.SizeY-48;
    C.StrLen("X", LineX, LineHeight);
    Y=0; LastOrder=-1;
    // 按触发顺序垂直堆叠活动字幕，各自到期，不互相替换。
    for (j=0; j<64; j++)
    {
        BestIndex=-1; BestOrder=2147483647;
        for (i=0; i<64; i++)
        {
            if (CaptionBegin[i] <= Level.TimeSeconds && CaptionEnd[i] > Level.TimeSeconds
                && CaptionOrder[i] > LastOrder && CaptionOrder[i] < BestOrder)
            {
                BestIndex=i; BestOrder=CaptionOrder[i];
            }
        }
        if (BestIndex<0) break;
        LastOrder=BestOrder;
        C.SetPos(0, Y);
        C.StrLen(CaptionText[BestIndex], X, LineY);
        C.bCenter=(LineY <= LineHeight);
        C.DrawText(CaptionText[BestIndex], false);
        Y += FMax(LineY,LineHeight) + 6;
    }
    C.OrgX=OldOrgX; C.OrgY=OldOrgY; C.ClipX=OldClipX; C.ClipY=OldClipY;
    C.Font=OldFont; C.bCenter=OldCenter; C.Style=OldStyle; C.DrawColor=OldColor;
    C.SetPos(0,0);
}
