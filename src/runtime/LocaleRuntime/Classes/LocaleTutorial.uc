// Tutorial-only opt-in adapter: retain tutorial rules and the original player tag.
class LocaleTutorial expands giTutorial;

event playerpawn Login(string Portal, string Options, out string Error,
    class<playerpawn> SpawnClass)
{
    local PlayerPawn Result;
    Result = Super(giWOT).Login(Portal, Options, Error, class'LocalePlayer');
    if (Result != None)
    {
        ChangeTeam(Result, 0);
        ChangeName(Result, "Elayna Sedai", false);
        Result.Tag = 'AesSedai';
    }
    return Result;
}
