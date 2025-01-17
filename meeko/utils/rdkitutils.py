from rdkit import Chem
from .utils import mini_periodic_table
from .pdbutils import PDBAtomInfo


"""
create new RDKIT residue

mi  =  Chem.AtomPDBResidueInfo()
mi.SetResidueName('MOL')
mi.SetResidueNumber(1)
mi.SetOccupancy(0.0)
mi.SetTempFactor(0.0)

source: https://sourceforge.net/p/rdkit/mailman/message/36404394/
"""


def getPdbInfoNoNull(atom):
    """extract information for populating an ATOM/HETATM line
    in the PDB"""
    minfo = atom.GetMonomerInfo()  # same as GetPDBResidueInfo
    if minfo is None:
        atomic_number = atom.GetAtomicNum()
        if atomic_number == 0:
            name = "%-2s" % "*"
        else:
            name = "%-2s" % mini_periodic_table[atomic_number]
        chain = " "
        resNum = 1
        icode = ""
        resName = "UNL"
    else:
        name = minfo.GetName()
        chain = minfo.GetChainId()
        resNum = minfo.GetResidueNumber()
        icode = minfo.GetInsertionCode()
        resName = minfo.GetResidueName()
    return PDBAtomInfo(
        name=name, resName=resName, resNum=resNum, icode=icode, chain=chain
    )


class Mol2MolSupplier:
    """RDKit Mol2 molecule supplier.
    Parameters
        sanitize: perform RDKit sanitization of Mol2 molecule"""

    def __init__(
        self, filename, sanitize=True, removeHs=False, cleanupSubstructures=True
    ):
        self.fp = open(filename, "r")
        self._opts = {
            "sanitize": sanitize,
            "removeHs": removeHs,
            "cleanupSubstructures": cleanupSubstructures,
        }
        self.buff = []

    def __iter__(self):
        return self

    def __next__(self):
        """iterator step"""
        while True:
            line = self.fp.readline()
            # empty line
            if not line:
                if len(self.buff):
                    # buffer full, returning last molecule
                    mol = Chem.MolFromMol2Block("".join(self.buff), **self._opts)
                    self.buff = []
                    return mol
                # buffer empty, stopping the iteration
                self.fp.close()
                raise StopIteration
            if "@<TRIPOS>MOLECULE" in line:
                # first molecule parsed
                if len(self.buff) == 0:
                    self.buff.append(line)
                else:
                    # found the next molecule, breaking to return the complete one
                    break
            else:
                # adding another line in the current molecule
                self.buff.append(line)
        # found a complete molecule, returning it
        mol = Chem.MolFromMol2Block("".join(self.buff), **self._opts)
        self.buff = [line]
        return mol


def react_and_map(reactants, rxn):
    """run reaction and keep track of atom indices from reagents to products"""

    # https://github.com/rdkit/rdkit/discussions/4327#discussioncomment-998612

    # keep track of the reactant that each atom belongs to
    for i, reactant in enumerate(reactants):
        for atom in reactant.GetAtoms():
            atom.SetIntProp("reactant_idx", i)

    reactive_atoms_idxmap = {}
    for i in range(rxn.GetNumReactantTemplates()):
        reactant_template = rxn.GetReactantTemplate(i)
        for atom in reactant_template.GetAtoms():
            if atom.GetAtomMapNum():
                reactive_atoms_idxmap[atom.GetAtomMapNum()] = i

    products_list = rxn.RunReactants(reactants)

    index_map = {"reactant_idx": [], "atom_idx": [], "new_atom_label": []}
    for products in products_list:
        result_reac_map = []
        result_atom_map = []
        new_atom_label_list = (
            []
        )  # for atoms created by the reaction that are labeled e.g. F in "[O:1]>>[O:1][F:2]"
        for product in products:
            atom_idxmap = []
            reac_idxmap = []
            new_atom_label = []
            for atom in product.GetAtoms():
                if atom.HasProp("reactant_idx"):
                    reactant_idx = atom.GetIntProp("reactant_idx")
                    new_atom_label.append(None)
                elif atom.HasProp("old_mapno"):  # this atom matched the reaction SMARTS
                    old_mapno = atom.GetIntProp("old_mapno")
                    if old_mapno in reactive_atoms_idxmap:
                        reactant_idx = reactive_atoms_idxmap[old_mapno]
                        new_atom_label.append(None)
                    else:
                        reactant_idx = None
                        new_atom_label.append(
                            old_mapno
                        )  # the reaction SMARTS created this atom and it has a label
                    # if atom.HasProp("reactant_idx"):
                    #    raise RuntimeError("did not expect both old_mapno and reactant_idx")
                    #    #print("did not expect both old_mapno and reactant_idx")
                else:
                    reactant_idx = None  # the reaction SMARTS creates new atoms
                    new_atom_label.append(None)
                reac_idxmap.append(reactant_idx)
                if atom.HasProp("react_atom_idx"):
                    atom_idxmap.append(atom.GetIntProp("react_atom_idx"))
                else:
                    atom_idxmap.append(None)
            result_reac_map.append(reac_idxmap)
            result_atom_map.append(atom_idxmap)
            new_atom_label_list.append(new_atom_label)
        index_map["reactant_idx"].append(result_reac_map)
        index_map["atom_idx"].append(result_atom_map)
        index_map["new_atom_label"].append(new_atom_label_list)

    return products_list, index_map
