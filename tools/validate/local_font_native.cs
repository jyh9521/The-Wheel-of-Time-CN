// Execute the emitted adapter from a real PE mapping; do not initialize UE globals.
using System;
using System.IO;
using System.Runtime.InteropServices;
public static class LoaderNativeTest {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr LoadLibraryExW(string file,IntPtr reserved,uint flags);
    [DllImport("kernel32.dll")] static extern bool FreeLibrary(IntPtr module);
    [DllImport("kernel32.dll",CharSet=CharSet.Ansi)] static extern IntPtr GetModuleHandleA(string name);
    [DllImport("kernel32.dll",CharSet=CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr module,string name);
    [DllImport("kernel32.dll")] static extern bool VirtualProtect(IntPtr address,UIntPtr size,uint protection,out uint old);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate void Loader();
    static void WritePointer(IntPtr baseAddress,int rva,IntPtr value) {
        IntPtr address=IntPtr.Add(baseAddress,rva);uint old;
        if(!VirtualProtect(address,(UIntPtr)4,0x40,out old)) throw new Exception("IAT protection failed");
        Marshal.WriteInt32(address,value.ToInt32()); uint ignored;VirtualProtect(address,(UIntPtr)4,old,out ignored);
    }
    [STAThread] public static int Main(string[] args) {
        IntPtr module=IntPtr.Zero;
        try {
            if(IntPtr.Size!=4 || args.Length!=5 || File.Exists(args[3])) throw new Exception("Need x86: patchedDLL QTSystem movie NEW.png time");
            // DONT_RESOLVE_DLL_REFERENCES: original UE imports/constructors are deliberately not executed.
            module=LoadLibraryExW(Path.GetFullPath(args[0]),IntPtr.Zero,1);
            if(module==IntPtr.Zero)throw new Exception("PE mapping failed: "+Marshal.GetLastWin32Error());
            IntPtr kernel=GetModuleHandleA("kernel32.dll");
            WritePointer(module,0x42dac,GetProcAddress(kernel,"GetModuleHandleA"));
            WritePointer(module,0x42dbc,GetProcAddress(kernel,"GetProcAddress"));
            WritePointer(module,0x42dc0,GetProcAddress(kernel,"LoadLibraryA"));
            // Replace only the tail target IN HARNESS MEMORY: real game must execute original InitializeQTML wrapper.
            uint old;IntPtr tail=IntPtr.Add(module,0x17e50);
            if(!VirtualProtect(tail,(UIntPtr)1,0x40,out old))throw new Exception("Tail protection failed");
            Marshal.WriteByte(tail,0xc3);uint ignored;VirtualProtect(tail,(UIntPtr)1,old,out ignored);
            Loader run=(Loader)Marshal.GetDelegateForFunctionPointer(IntPtr.Add(module,0x50000),typeof(Loader));
            run();int first=Marshal.ReadInt32(IntPtr.Add(module,0x51000));run();int second=Marshal.ReadInt32(IntPtr.Add(module,0x51000));
            if(first<=0 || second!=first)throw new Exception("Adapter did not register the local font");
            Console.WriteLine("NATIVE LOADER PASS: actual PE adapter; faces="+first+"; cached="+second+"; module-relative path; no UE constructors/game launched");
            using(NativeMovie movie=new NativeMovie(args[1],args[2],true)) {
                movie.Seek(double.Parse(args[4],System.Globalization.CultureInfo.InvariantCulture));movie.Frame.Save(args[3]);
                Console.WriteLine("NATIVE LOADER RENDER PASS: 1920x1080; actual adapter before QuickTime initialization");
            }
            return 0;
        }catch(Exception e){Console.Error.WriteLine(e);return 1;}
        finally{if(module!=IntPtr.Zero)FreeLibrary(module);}
    }
}
