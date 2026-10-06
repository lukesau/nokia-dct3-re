// Mark the DCT4 flash entry (ARM state at 0x01000100) before auto-analysis.
// The rest of the image is mostly Thumb; the aggressive instruction finder
// picks that up from the calls out of the entry.
//
// Also turns off "Non-Returning Functions - Discovered": on this image it
// marks malloc/free (file/line-traced, 3000+ callers each) and ~330 others as
// non-returning, which cuts disassembly and decompilation off after every call.
// @category Nokia3510

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.symbol.SourceType;

public class SetDct4Entry extends GhidraScript {
	@Override
	protected void run() throws Exception {
		setAnalysisOption(currentProgram, "Non-Returning Functions - Discovered", "false");
		var entry = toAddr(0x01000100);
		new DisassembleCommand(new AddressSet(entry, entry), null, true).applyTo(currentProgram, monitor);
		if (getFunctionAt(entry) == null)
			createFunction(entry, "flash_entry_1000100");
		currentProgram.getSymbolTable().addExternalEntryPoint(entry);
		currentProgram.getSymbolTable().createLabel(toAddr(0x015a0000), "ppm_start", SourceType.USER_DEFINED);
	}
}
