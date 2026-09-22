# PhysMAP Closure-Index Expansion — Candidate Table (v0.1, for author review)

**Status:** APPROVED 2026-06-09 and **MERGED** — this table is now the source of truth that
`physmap.closures.index.build_index_json()` parses; the bundled `closure_index.json` carries all
**200** closures (52 corpus + churchill + 147 case-2b candidates). Rebuild with
`python -m physmap.closures.index --rebuild`. **Author:** drafted by Claude Code, June 9 2026 ·
anchored on the 52 curated `corpus.jsonl` closures + the handbook shelf (Incropera & DeWitt, Rohsenow
Handbook, VDI Heat Atlas, ESDU) + solver docs, framed by
`PhysMAP_ClosureDivergence_Evidence_Search_Handoff_Spec_v0_2.md`.

## What this is

The open **closure index** (`physmap/closures/index.py` → `CLOSURE_INDEX`) is metadata-only:
`closure_id, closure_name, closure_family, geometry_class, physics_coordinates, citation, aliases`
— **no ranges, no provenance, no disposition**. It already carries the **53** known closures
(52 corpus + `churchill-mixed-convection-flat-plate`). This document adds **147 new metadata-only
candidates** (→ **200 total**), each a **case-2b** closure by construction (registered, no bounds —
they fire the "registered; bounds not yet curated, file an issue" path until/unless a future corpus
entry curates bounds).

**Rules honored:** every row has a **real primary citation** (author-year-venue); uncertain
attributions are excluded and listed in §16. Family-name decisions are in §14. No corpus entries
are created. Coordinates use the corpus vocabulary where one exists; proposed new coordinate names
are flagged in §15.

## Summary (proposed counts)

| Family | New candidates | Status |
|---|---:|---|
| **— Tranche 1 —** | | |
| condensation (new family) | 9 | approved |
| external-convection (new family) | 11 | approved |
| natural-convection (new family) | 10 | approved |
| rans-turbulence + LES + wall-function | 18 | approved |
| multiphase interfacial | 10 | approved |
| radiation (new family) | 6 | approved |
| single-phase-convection (ducts, from §7 split) | 9 | approved |
| hydraulic-friction (new family, §7 split) | 5 | approved |
| transfer-analogy (new family, §7 split) | 4 | approved |
| surface-enhancement (new family, §7 split) | 9 | approved |
| packed-porous (new family, §7 split) | 3 | approved |
| domain — cardio (hemolysis/thrombosis/rheology) | 10 | approved |
| domain — aero (compressible/ablation/stagnation) | 14 | approved |
| **— Tranche 2 —** | | |
| combustion-kinetics | 9 | approved |
| species-diffusion | 7 | approved |
| non-newtonian-rheology (additional) | 8 | approved |
| rarefied-gas (new family) | 5 | approved |
| **Total new** | **147** | |
| Existing index | 53 | shipped |
| **Grand total** | **200** | on target |

---

## 1. condensation  *(new family — author-approve the family name)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| nusselt-film-condensation-1916 | Nusselt laminar film condensation | film_reynolds_number, jakob_number | Nusselt, W. (1916). "Die Oberflächenkondensation des Wasserdampfes." VDI Z. 60:541–546, 569–575 | Nusselt film, film condensation |
| rohsenow-condensation-subcooling-1956 | Rohsenow subcooling-corrected film condensation | jakob_number, prandtl_number | Rohsenow, W.M. (1956). "Heat transfer and temperature distribution in laminar film condensation." Trans. ASME 78:1645–1648 | Rohsenow condensation |
| chato-condensation-horizontal-tube-1962 | Chato laminar condensation in horizontal tubes | vapor_reynolds_number | Chato, J.C. (1962). "Laminar condensation inside horizontal and inclined tubes." ASHRAE J. 4:52–60 | Chato |
| akers-condensation-1959 | Akers–Deans–Crosser in-tube condensation | equivalent_reynolds_number, prandtl_number | Akers, W.W., Deans, H.A., Crosser, O.K. (1959). "Condensing heat transfer within horizontal tubes." Chem. Eng. Prog. Symp. Ser. 55(29):171–176 | Akers |
| shah-condensation-1979 | Shah general in-tube condensation | reduced_pressure, vapor_quality, mass_flux | Shah, M.M. (1979). "A general correlation for heat transfer during film condensation inside pipes." Int. J. Heat Mass Transfer 22(4):547–556 | Shah condensation |
| traviss-condensation-1973 | Traviss–Rohsenow–Baron annular condensation | martinelli_parameter, vapor_quality | Traviss, D.P., Rohsenow, W.M., Baron, A.B. (1973). "Forced-convection condensation inside tubes." ASHRAE Trans. 79:157–165 | Traviss |
| dobson-chato-condensation-1998 | Dobson–Chato flow-regime condensation | mass_flux, vapor_quality | Dobson, M.K., Chato, J.C. (1998). "Condensation in smooth horizontal tubes." J. Heat Transfer 120(1):193–213 | Dobson-Chato |
| thome-condensation-2003 | Thome–El Hajal–Cavallini flow-regime model | mass_flux, vapor_quality | Thome, J.R., El Hajal, J., Cavallini, A. (2003). "Condensation in horizontal tubes, part 2." Int. J. Heat Mass Transfer 46(18):3365–3387 | Thome condensation |
| cavallini-condensation-2006 | Cavallini et al. in-tube condensation model | mass_flux, reduced_pressure, vapor_quality | Cavallini, A. et al. (2006). "Condensation in horizontal smooth tubes: a new heat transfer model." Heat Transfer Eng. 27(8):31–38 | Cavallini |

## 2. external-convection

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| hilpert-cylinder-crossflow-1933 | Hilpert cylinder cross-flow | reynolds_number, prandtl_number | Hilpert, R. (1933). "Wärmeabgabe von geheizten Drähten und Rohren im Luftstrom." Forsch. Geb. Ingenieurwes. 4(5):215–224 | Hilpert |
| churchill-bernstein-cylinder-1977 | Churchill–Bernstein cylinder cross-flow | reynolds_number, prandtl_number | Churchill, S.W., Bernstein, M. (1977). "A correlating equation for forced convection from gases and liquids to a circular cylinder in crossflow." J. Heat Transfer 99(2):300–306 | Churchill-Bernstein |
| zukauskas-cylinder-1972 | Žukauskas single-cylinder cross-flow | reynolds_number, prandtl_number, prandtl_ratio_bulk_wall | Žukauskas, A. (1972). "Heat transfer from tubes in crossflow." Adv. Heat Transfer 8:93–160 | Zukauskas cylinder |
| zukauskas-tube-bank-1972 | Žukauskas tube-bank cross-flow (inline & staggered) | reynolds_number, prandtl_number | Žukauskas, A. (1972). "Heat transfer from tubes in crossflow." Adv. Heat Transfer 8:93–160 | Zukauskas tube bank, staggered tube bank, inline tube bank |
| grimison-tube-bank-1937 | Grimison tube-bank cross-flow | reynolds_number | Grimison, E.D. (1937). "Correlation and utilization of new data on flow resistance and heat transfer for cross flow of gases over tube banks." Trans. ASME 59:583–594 | Grimison |
| fand-cylinder-1965 | Fand cylinder cross-flow in liquids | reynolds_number, prandtl_number | Fand, R.M. (1965). "Heat transfer by forced convection from a cylinder to water in crossflow." Int. J. Heat Mass Transfer 8(7):995–1010 | Fand |
| perkins-leppert-cylinder-1964 | Perkins–Leppert cylinder cross-flow | reynolds_number, prandtl_number, prandtl_ratio_bulk_wall | Perkins, H.C., Leppert, G. (1964). "Local heat-transfer coefficients on a uniformly heated cylinder." Int. J. Heat Mass Transfer 7(2):143–158 | Perkins-Leppert |
| ranz-marshall-sphere-1952 | Ranz–Marshall sphere/droplet | reynolds_number, prandtl_number | Ranz, W.E., Marshall, W.R. (1952). "Evaporation from drops." Chem. Eng. Prog. 48:141–146, 173–180 | Ranz-Marshall |
| whitaker-cylinder-1972 | Whitaker cylinder cross-flow | reynolds_number, prandtl_number, prandtl_ratio_bulk_wall | Whitaker, S. (1972). "Forced convection heat transfer correlations for flow in pipes, past flat plates, single cylinders, single spheres, and for flow in packed beds and tube bundles." AIChE J. 18(2):361–371 | Whitaker cylinder |
| jakob-tube-bank-1949 | Jakob tube-bank correlation | reynolds_number | Jakob, M. (1949). "Heat Transfer, Vol. 1." Wiley, Ch. 24 | Jakob bank |
| morgan-cylinder-1975 | Morgan cylinder convective survey | reynolds_number, prandtl_number | Morgan, V.T. (1975). "The overall convective heat transfer from smooth circular cylinders." Adv. Heat Transfer 11:199–264 | Morgan |

## 3. natural-convection

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| churchill-chu-vertical-plate-1975 | Churchill–Chu vertical plate (all-Ra) | rayleigh_number, prandtl_number | Churchill, S.W., Chu, H.H.S. (1975). "Correlating equations for laminar and turbulent free convection from a vertical plate." Int. J. Heat Mass Transfer 18(11):1323–1329 | Churchill-Chu plate |
| churchill-chu-horizontal-cylinder-1975 | Churchill–Chu horizontal cylinder | rayleigh_number, prandtl_number | Churchill, S.W., Chu, H.H.S. (1975). "Correlating equations for laminar and turbulent free convection from a horizontal cylinder." Int. J. Heat Mass Transfer 18(9):1049–1053 | Churchill-Chu cylinder |
| raithby-hollands-enclosure-1975 | Raithby–Hollands enclosure method | rayleigh_number, prandtl_number | Raithby, G.D., Hollands, K.G.T. (1975). "A general method of obtaining approximate solutions to laminar and turbulent free convection problems." Adv. Heat Transfer 11:265–315 | Raithby-Hollands |
| globe-dropkin-enclosure-1959 | Globe–Dropkin heated-from-below layer | rayleigh_number, prandtl_number | Globe, S., Dropkin, D. (1959). "Natural-convection heat transfer in liquids confined by two horizontal plates and heated from below." J. Heat Transfer 81:24–28 | Globe-Dropkin |
| macgregor-emery-cavity-1969 | MacGregor–Emery vertical cavity | rayleigh_number, prandtl_number | MacGregor, R.K., Emery, A.F. (1969). "Free convection through vertical plane layers." J. Heat Transfer 91(3):391–401 | MacGregor-Emery |
| catton-enclosure-1978 | Catton enclosure correlations | rayleigh_number | Catton, I. (1978). "Natural convection in enclosures." Proc. 6th Int. Heat Transfer Conf. 6:13–31 | Catton |
| lloyd-moran-horizontal-plate-1974 | Lloyd–Moran horizontal plate | rayleigh_number | Lloyd, J.R., Moran, W.R. (1974). "Natural convection adjacent to horizontal surface of various planforms." J. Heat Transfer 96(4):443–447 | Lloyd-Moran |
| fujii-imura-inclined-plate-1972 | Fujii–Imura inclined plate | rayleigh_number | Fujii, T., Imura, H. (1972). "Natural-convection heat transfer from a plate with arbitrary inclination." Int. J. Heat Mass Transfer 15(4):755–767 | Fujii-Imura |
| churchill-chu-sphere-1983 | Churchill sphere free convection | rayleigh_number, prandtl_number | Churchill, S.W. (1983). "Free convection around immersed bodies." in Heat Exchanger Design Handbook, §2.5.7 | Churchill sphere |
| bar-cohen-rohsenow-channel-1984 | Bar-Cohen–Rohsenow vertical channel | rayleigh_number | Bar-Cohen, A., Rohsenow, W.M. (1984). "Thermally optimum spacing of vertical, natural convection cooled, parallel plates." J. Heat Transfer 106(1):116–123 | Bar-Cohen-Rohsenow |

## 4. rans-turbulence + LES + wall-function

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| launder-sharma-low-re-1974 | Launder–Sharma low-Re k–ε | turbulence_reynolds_number | Launder, B.E., Sharma, B.I. (1974). "Application of the energy-dissipation model of turbulence to the calculation of flow near a spinning disc." Lett. Heat Mass Transfer 1(2):131–137 | Launder-Sharma |
| yakhot-orszag-rng-1986 | RNG k–ε | reynolds_number | Yakhot, V., Orszag, S.A. (1986). "Renormalization group analysis of turbulence." J. Sci. Comput. 1(1):3–51 | RNG k-epsilon |
| shih-realizable-k-epsilon-1995 | Realizable k–ε | reynolds_number | Shih, T.-H. et al. (1995). "A new k–ε eddy viscosity model for high Reynolds number turbulent flows." Comput. Fluids 24(3):227–238 | realizable k-epsilon |
| abe-kondoh-nagano-1994 | Abe–Kondoh–Nagano low-Re k–ε | turbulence_reynolds_number, wall_y_plus | Abe, K., Kondoh, T., Nagano, Y. (1994). "A new turbulence model for predicting fluid flow and heat transfer in separating and reattaching flows." Int. J. Heat Mass Transfer 37(1):139–151 | AKN |
| launder-reece-rodi-rsm-1975 | LRR Reynolds-stress model | anisotropy_invariant | Launder, B.E., Reece, G.J., Rodi, W. (1975). "Progress in the development of a Reynolds-stress turbulence closure." J. Fluid Mech. 68(3):537–566 | LRR, RSM |
| speziale-sarkar-gatski-rsm-1991 | SSG pressure–strain RSM | anisotropy_invariant | Speziale, C.G., Sarkar, S., Gatski, T.B. (1991). "Modelling the pressure–strain correlation of turbulence." J. Fluid Mech. 227:245–272 | SSG |
| gibson-launder-rsm-1978 | Gibson–Launder wall-reflection RSM | anisotropy_invariant, wall_y_plus | Gibson, M.M., Launder, B.E. (1978). "Ground effects on pressure fluctuations in the atmospheric boundary layer." J. Fluid Mech. 86(3):491–511 | Gibson-Launder |
| menter-baseline-komega-1994 | Menter BSL k–ω | wall_y_plus | Menter, F.R. (1994). "Two-equation eddy-viscosity turbulence models for engineering applications." AIAA J. 32(8):1598–1605 | BSL, baseline k-omega |
| wilcox-low-re-komega-1994 | Wilcox low-Re k–ω | turbulence_reynolds_number | Wilcox, D.C. (1994). "Simulation of transition with a two-equation turbulence model." AIAA J. 32(2):247–255 | Wilcox low-Re |
| smagorinsky-sgs-1963 | Smagorinsky SGS model | grid_filter_ratio | Smagorinsky, J. (1963). "General circulation experiments with the primitive equations." Mon. Weather Rev. 91(3):99–164 | Smagorinsky |
| germano-dynamic-sgs-1991 | Germano dynamic SGS | grid_filter_ratio | Germano, M., Piomelli, U., Moin, P., Cabot, W.H. (1991). "A dynamic subgrid-scale eddy viscosity model." Phys. Fluids A 3(7):1760–1765 | dynamic Smagorinsky |
| lilly-dynamic-1992 | Lilly least-squares dynamic SGS | grid_filter_ratio | Lilly, D.K. (1992). "A proposed modification of the Germano subgrid-scale closure method." Phys. Fluids A 4(3):633–635 | Lilly |
| nicoud-ducros-wale-1999 | WALE SGS | wall_distance | Nicoud, F., Ducros, F. (1999). "Subgrid-scale stress modelling based on the square of the velocity gradient tensor." Flow Turbul. Combust. 62(3):183–200 | WALE |
| vreman-sgs-2004 | Vreman SGS | grid_filter_ratio | Vreman, A.W. (2004). "An eddy-viscosity subgrid-scale model for turbulent shear flow." Phys. Fluids 16(10):3670–3681 | Vreman |
| spalding-law-of-the-wall-1961 | Spalding single-formula wall law | wall_y_plus | Spalding, D.B. (1961). "A single formula for the law of the wall." J. Appl. Mech. 28(3):455–458 | Spalding wall |
| van-driest-damping-1956 | Van Driest mixing-length damping | wall_y_plus | Van Driest, E.R. (1956). "On turbulent flow near a wall." J. Aeronaut. Sci. 23(11):1007–1011 | Van Driest damping |
| kader-temperature-wall-1981 | Kader thermal wall function | wall_y_plus, prandtl_number | Kader, B.A. (1981). "Temperature and concentration profiles in fully turbulent boundary layers." Int. J. Heat Mass Transfer 24(9):1541–1544 | Kader |
| jayatilleke-p-function-1969 | Jayatilleke P-function (thermal sublayer) | prandtl_number | Jayatilleke, C.L.V. (1969). "The influence of Prandtl number and surface roughness on the resistance of the laminar sublayer to momentum and heat transfer." Prog. Heat Mass Transfer 1:193–330 | Jayatilleke P |

## 5. multiphase interfacial *(extends interfacial-force)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| schiller-naumann-drag-1935 | Schiller–Naumann particle drag | particle_reynolds_number | Schiller, L., Naumann, A. (1935). "Über die grundlegenden Berechnungen bei der Schwerkraftaufbereitung." VDI Z. 77:318–320 | Schiller-Naumann |
| ishii-zuber-drag-1979 | Ishii–Zuber drag (distorted/cap regimes) | particle_reynolds_number, eotvos_number | Ishii, M., Zuber, N. (1979). "Drag coefficient and relative velocity in bubbly, droplet or particulate flows." AIChE J. 25(5):843–855 | Ishii-Zuber |
| grace-wairegi-nguyen-drag-1976 | Grace–Wairegi–Nguyen bubble/drop drag (Eo–Mo) | eotvos_number, morton_number | Grace, J.R., Wairegi, T., Nguyen, T.H. (1976). "Shapes and velocities of single drops and bubbles moving freely through immiscible liquids." Trans. Inst. Chem. Eng. 54:167–173 | Grace, Grace drag |
| antal-wall-force-1991 | Antal wall-lubrication force | bubble_reynolds_number | Antal, S.P., Lahey, R.T., Flaherty, J.E. (1991). "Analysis of phase distribution in fully developed laminar bubbly two-phase flow." Int. J. Multiphase Flow 17(5):635–652 | Antal |
| legendre-magnaudet-lift-1998 | Legendre–Magnaudet shear lift | bubble_reynolds_number | Legendre, D., Magnaudet, J. (1998). "The lift force on a spherical bubble in a viscous linear shear flow." J. Fluid Mech. 368:81–126 | Legendre-Magnaudet |
| burns-turbulent-dispersion-2004 | Burns FAD turbulent dispersion | eotvos_number | Burns, A.D., Frank, T., Hamill, I., Shi, J.-M. (2004). "The Favre averaged drag model for turbulent dispersion in Eulerian multi-phase flows." 5th Int. Conf. Multiphase Flow, ICMF | Burns FAD |
| lopez-de-bertodano-dispersion-1991 | Lopez de Bertodano turbulent dispersion | turbulent_kinetic_energy | Lopez de Bertodano, M. (1991). "Turbulent bubbly two-phase flow in a triangular duct." PhD thesis, RPI | Lopez de Bertodano |
| sato-bubble-turbulence-1981 | Sato bubble-induced turbulence | void_fraction, bubble_reynolds_number | Sato, Y., Sadatomi, M., Sekoguchi, K. (1981). "Momentum and heat transfer in two-phase bubble flow." Int. J. Multiphase Flow 7(2):167–177 | Sato BIT |
| hibiki-ishii-interfacial-area-2002 | Hibiki–Ishii interfacial-area transport | void_fraction, bubble_reynolds_number | Hibiki, T., Ishii, M. (2002). "Development of one-group interfacial area transport equation in bubbly flow systems." Int. J. Heat Mass Transfer 45(11):2351–2372 | Hibiki-Ishii IATE |
| moraga-lift-1999 | Moraga lift (sign-change) | bubble_reynolds_number | Moraga, F.J., Bonetto, F.J., Lahey, R.T. (1999). "Lateral forces on spheres in turbulent uniform shear flow." Int. J. Multiphase Flow 25(6):1321–1372 | Moraga |

## 6. radiation *(new family — author-approve)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| hottel-gas-emissivity-1967 | Hottel gas emissivity charts | optical_thickness, temperature | Hottel, H.C., Sarofim, A.F. (1967). "Radiative Transfer." McGraw-Hill, Ch. 6 | Hottel charts |
| leckner-gas-emissivity-1972 | Leckner CO₂/H₂O emissivity | partial_pressure_path, temperature | Leckner, B. (1972). "Spectral and total emissivity of water vapor and carbon dioxide." Combust. Flame 19(1):33–48 | Leckner |
| modest-wsgg-1991 | Weighted-sum-of-gray-gases | optical_thickness | Modest, M.F. (1991). "The weighted-sum-of-gray-gases model for arbitrary solution methods in radiative transfer." J. Heat Transfer 113(3):650–656 | WSGG |
| rosseland-diffusion-1936 | Rosseland optically-thick diffusion | optical_thickness | Rosseland, S. (1936). "Theoretical Astrophysics." Oxford Univ. Press | Rosseland |
| chandrasekhar-discrete-ordinates-1950 | Discrete-ordinates (S_N) radiation | optical_thickness | Chandrasekhar, S. (1950). "Radiative Transfer." Oxford Univ. Press | DOM, S_N |
| smith-wsgg-1982 | Smith–Shen–Friedman WSGG coefficients | optical_thickness | Smith, T.F., Shen, Z.F., Friedman, J.N. (1982). "Evaluation of coefficients for the weighted sum of gray gases model." J. Heat Transfer 104(4):602–608 | Smith WSGG |

## 7. Internal flow, friction & enhancement  *(the §7 grab-bag, split into five families per review)*

> Review note: the original "internal-enhancement" mixed genuine enhancement with plain duct
> convection, friction factors, and transfer analogies. Split below. Family is public metadata, so a
> grab-bag reads as uncurated — these five families each stand on their own.

### 7a. single-phase-convection  *(plain internal-flow ducts — existing corpus family)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| gnielinski-annulus-2009 | Gnielinski turbulent annular duct | reynolds_number, prandtl_number | Gnielinski, V. (2009). "Heat transfer coefficients for turbulent flow in concentric annular ducts." Heat Transfer Eng. 30(6):431–436 | Gnielinski annulus |
| graetz-laminar-entry-1885 | Graetz thermal-entry problem | graetz_number | Graetz, L. (1885). "Über die Wärmeleitungsfähigkeit von Flüssigkeiten." Ann. Phys. 261(7):337–357 | Graetz |
| hausen-laminar-entry-1943 | Hausen laminar thermal-entry | graetz_number | Hausen, H. (1943). "Darstellung des Wärmeüberganges in Rohren durch verallgemeinerte Potenzbeziehungen." VDI-Z. Beiheft Verfahrenstechnik 4:91–98 | Hausen |
| notter-sleicher-1972 | Notter–Sleicher turbulent pipe | reynolds_number, prandtl_number | Notter, R.H., Sleicher, C.A. (1972). "A solution to the turbulent Graetz problem." Chem. Eng. Sci. 27(11):2073–2093 | Notter-Sleicher |
| sleicher-rouse-1975 | Sleicher–Rouse pipe correlation | reynolds_number, prandtl_number | Sleicher, C.A., Rouse, M.W. (1975). "A convenient correlation for heat transfer to constant and variable property fluids in turbulent pipe flow." Int. J. Heat Mass Transfer 18(5):677–683 | Sleicher-Rouse |
| seban-shimazaki-liquid-metal-1951 | Seban–Shimazaki liquid-metal pipe | peclet_number | Seban, R.A., Shimazaki, T.T. (1951). "Heat transfer to a fluid flowing turbulently in a smooth pipe with walls at constant temperature." Trans. ASME 73:803–809 | liquid metal Nu |
| skupinski-liquid-metal-1965 | Skupinski liquid-metal uniform-flux | peclet_number | Skupinski, E., Tortel, J., Vautrey, L. (1965). "Détermination des coefficients de convection d'un alliage sodium-potassium." Int. J. Heat Mass Transfer 8(6):937–951 | Skupinski |
| kays-crawford-turbulent-prandtl-1994 | Kays variable turbulent-Prandtl | peclet_number, prandtl_number | Kays, W.M. (1994). "Turbulent Prandtl number — where are we?" J. Heat Transfer 116(2):284–295 | Kays Pr_t |
| churchill-usagi-1972 | Churchill–Usagi asymptotic blending | blending_exponent | Churchill, S.W., Usagi, R. (1972). "A general expression for the correlation of rates of transfer and other phenomena." AIChE J. 18(6):1121–1128 | Churchill-Usagi |

### 7b. hydraulic-friction  *(NEW family — friction factors)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| blasius-friction-1913 | Blasius smooth-pipe friction | reynolds_number | Blasius, H. (1913). "Das Ähnlichkeitsgesetz bei Reibungsvorgängen in Flüssigkeiten." Forsch. Geb. Ingenieurwes. 131 | Blasius friction |
| colebrook-white-friction-1939 | Colebrook–White friction factor | reynolds_number, relative_roughness | Colebrook, C.F. (1939). "Turbulent flow in pipes, with particular reference to the transition region between the smooth and rough pipe laws." J. Inst. Civ. Eng. 11(4):133–156 | Colebrook |
| filonenko-friction-1954 | Filonenko friction factor | reynolds_number | Filonenko, G.K. (1954). "Hydraulic resistance in pipes." Teploenergetika 1(4):40–44 | Filonenko |
| petukhov-friction-1970 | Petukhov turbulent friction factor | reynolds_number | Petukhov, B.S. (1970). "Heat transfer and friction in turbulent pipe flow with variable physical properties." Adv. Heat Transfer 6:503–564 | Petukhov friction |
| haaland-friction-1983 | Haaland explicit friction factor | reynolds_number, relative_roughness | Haaland, S.E. (1983). "Simple and explicit formulas for the friction factor in turbulent pipe flow." J. Fluids Eng. 105(1):89–90 | Haaland |

### 7c. transfer-analogy  *(NEW family — momentum/heat/mass analogies)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| reynolds-analogy-1874 | Reynolds analogy | reynolds_number | Reynolds, O. (1874). "On the extent and action of the heating surface of steam boilers." Proc. Manchester Lit. Phil. Soc. 14:7–12 | Reynolds analogy |
| colburn-j-factor-1933 | Colburn j-factor analogy | reynolds_number, prandtl_number | Colburn, A.P. (1933). "A method of correlating forced convection heat transfer data and a comparison with fluid friction." Trans. AIChE 29:174–210 | Colburn analogy |
| chilton-colburn-analogy-1934 | Chilton–Colburn momentum/heat/mass analogy | reynolds_number, prandtl_number, schmidt_number | Chilton, T.H., Colburn, A.P. (1934). "Mass transfer (absorption) coefficients." Ind. Eng. Chem. 26(11):1183–1187 | Chilton-Colburn |
| von-karman-analogy-1939 | von Kármán momentum/heat analogy | reynolds_number, prandtl_number | von Kármán, T. (1939). "The analogy between fluid friction and heat transfer." Trans. ASME 61:705–710 | Karman analogy |

### 7d. surface-enhancement  *(renamed from internal-enhancement — ribs / tapes / fins / coils / jets)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| martin-jet-impingement-1977 | Martin impinging jets | reynolds_number, prandtl_number | Martin, H. (1977). "Heat and mass transfer between impinging gas jets and solid surfaces." Adv. Heat Transfer 13:1–60 | Martin jet |
| goldstein-behbahani-jet-1982 | Goldstein round-jet impingement | reynolds_number | Goldstein, R.J., Behbahani, A.I. (1982). "Impingement of a circular jet with and without cross flow." Int. J. Heat Mass Transfer 25(9):1377–1382 | Goldstein jet |
| manglik-bergles-twisted-tape-1993 | Manglik–Bergles twisted-tape inserts | reynolds_number, swirl_parameter | Manglik, R.M., Bergles, A.E. (1993). "Heat transfer and pressure drop correlations for twisted-tape inserts in isothermal tubes." J. Heat Transfer 115(4):881–896 | twisted tape |
| webb-rib-roughness-1971 | Webb–Eckert–Goldstein ribbed tubes | reynolds_number, roughness_reynolds_number | Webb, R.L., Eckert, E.R.G., Goldstein, R.J. (1971). "Heat transfer and friction in tubes with repeated-rib roughness." Int. J. Heat Mass Transfer 14(4):601–617 | rib roughness |
| dipprey-sabersky-roughness-1963 | Dipprey–Sabersky rough-tube heat transfer | roughness_reynolds_number, prandtl_number | Dipprey, D.F., Sabersky, R.H. (1963). "Heat and momentum transfer in smooth and rough tubes at various Prandtl numbers." Int. J. Heat Mass Transfer 6(5):329–353 | Dipprey-Sabersky |
| mori-nakayama-curved-pipe-1965 | Mori–Nakayama curved-pipe heat transfer | dean_number, prandtl_number | Mori, Y., Nakayama, W. (1965). "Study on forced convective heat transfer in curved pipes (1st report)." Int. J. Heat Mass Transfer 8(1):67–82 | Mori-Nakayama |
| seban-mclaughlin-coil-1963 | Seban–McLaughlin helical coil | dean_number, prandtl_number | Seban, R.A., McLaughlin, E.F. (1963). "Heat transfer in tube coils with laminar and turbulent flow." Int. J. Heat Mass Transfer 6(5):387–395 | coil |
| schmidt-fin-efficiency-1949 | Schmidt fin efficiency | fin_parameter | Schmidt, T.E. (1949). "Heat transfer calculations for extended surfaces." Refrig. Eng. 57:351–357 | Schmidt fin |
| briggs-young-finned-bank-1963 | Briggs–Young finned-tube bank | reynolds_number | Briggs, D.E., Young, E.H. (1963). "Convection heat transfer and pressure drop of air flowing across triangular pitch banks of finned tubes." Chem. Eng. Prog. Symp. Ser. 59(41):1–10 | Briggs-Young |

### 7e. packed-porous  *(NEW family — packed beds / porous media)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| ergun-packed-bed-1952 | Ergun packed-bed pressure drop | particle_reynolds_number, void_fraction | Ergun, S. (1952). "Fluid flow through packed columns." Chem. Eng. Prog. 48:89–94 | Ergun |
| wakao-kaguei-packed-bed-1982 | Wakao–Kaguei packed-bed Nu | particle_reynolds_number, prandtl_number | Wakao, N., Kaguei, S. (1982). "Heat and Mass Transfer in Packed Beds." Gordon & Breach | Wakao-Kaguei |
| forchheimer-porous-1901 | Forchheimer inertial porous drag | pore_reynolds_number, porosity | Forchheimer, P. (1901). "Wasserbewegung durch Boden." VDI Z. 45:1782–1788 | Forchheimer |

## 8. domain — cardio (hemolysis / thrombosis / rheology) *(extends hemolysis, non-newtonian-rheology)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| garon-farinas-hemolysis-2004 | Garon–Farinas Eulerian hemolysis | shear_stress, exposure_time | Garon, A., Farinas, M.-I. (2004). "Fast three-dimensional numerical hemolysis approximation." Artif. Organs 28(11):1016–1025 | Eulerian hemolysis |
| zhang-hemolysis-2011 | Zhang power-law hemolysis (couette-calibrated) | shear_stress, exposure_time | Zhang, T. et al. (2011). "Study of flow-induced hemolysis using novel Couette-type blood-shearing devices." Artif. Organs 35(12):1180–1186 | Zhang hemolysis |
| goubergrits-affeld-hemolysis-2006 | Goubergrits–Affeld hemolysis model | shear_stress, exposure_time | Goubergrits, L., Affeld, K. (2006). "Numerical estimation of blood damage in artificial organs." Artif. Organs 30(5):408–416 | Goubergrits |
| arwatz-smits-hemolysis-2013 | Arwatz–Smits viscoelastic hemolysis | shear_stress, exposure_time | Arwatz, G., Smits, A.J. (2013). "A viscoelastic model of shear-induced hemolysis in laminar flow." Biorheology 50(1–2):45–55 | Arwatz |
| hellums-platelet-1994 | Hellums platelet-activation threshold | shear_stress, exposure_time | Hellums, J.D. (1994). "Whitaker Lecture: biorheology in thrombosis research." Ann. Biomed. Eng. 22(5):445–455 | Hellums threshold |
| soares-platelet-2013 | Soares stress-accumulation platelet model | shear_stress, exposure_time | Soares, J.S. et al. (2013). "A novel mathematical model of activation and sensitization of platelets subjected to dynamic stress histories." Biomech. Model. Mechanobiol. 12(6):1127–1141 | Soares platelet |
| taylor-thrombosis-2016 | Taylor multi-constituent thrombosis | shear_stress, residence_time | Taylor, J.O. et al. (2016). "Development of a computational model for macroscopic predictions of device-induced thrombosis." Biomech. Model. Mechanobiol. 15(6):1713–1731 | Taylor thrombosis |
| quemada-blood-1978 | Quemada concentrated-suspension viscosity | shear_rate, hematocrit | Quemada, D. (1978). "Rheology of concentrated disperse systems II." Rheol. Acta 17(6):632–642 | Quemada |
| walburn-schneck-blood-1976 | Walburn–Schneck blood viscosity | shear_rate, hematocrit | Walburn, F.J., Schneck, D.J. (1976). "A constitutive equation for whole human blood." Biorheology 13(3):201–210 | Walburn-Schneck |
| power-law-blood-rheology | Power-law (Ostwald–de Waele) blood model | shear_rate | Ostwald, W. (1925). "Über die Geschwindigkeitsfunktion der Viskosität disperser Systeme." Kolloid-Z. 36:99–117 | power-law fluid |

## 9. domain — aero (compressible / ablation / stagnation)

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| van-driest-ii-skin-friction-1956 | Van Driest II compressible skin friction | mach_number, reynolds_number | Van Driest, E.R. (1956). "The problem of aerodynamic heating." Aeronaut. Eng. Rev. 15(10):26–41 | Van Driest II |
| spalding-chi-1964 | Spalding–Chi compressible skin friction | mach_number, reynolds_number | Spalding, D.B., Chi, S.W. (1964). "The drag of a compressible turbulent boundary layer on a smooth flat plate with and without heat transfer." J. Fluid Mech. 18(1):117–143 | Spalding-Chi |
| white-christoph-compressible-1972 | White–Christoph compressible law-of-wall | mach_number, wall_y_plus | White, F.M., Christoph, G.H. (1972). "A simple new analysis of compressible turbulent two-dimensional skin friction under arbitrary conditions." AFFDL-TR-70-133 | White-Christoph |
| crocco-busemann-1932 | Crocco–Busemann temperature–velocity | mach_number, prandtl_number | Crocco, L. (1932). "Sulla trasmissione del calore da una lamina piana a un fluido scorrente ad alta velocità." L'Aerotecnica 12:181–197 | Crocco-Busemann |
| sutherland-viscosity-1893 | Sutherland viscosity law | temperature_ratio | Sutherland, W. (1893). "The viscosity of gases and molecular force." Phil. Mag. 36(223):507–531 | Sutherland |
| keyes-viscosity-1951 | Keyes viscosity correlation | temperature_ratio | Keyes, F.G. (1951). "A summary of viscosity and heat conduction data for He, A, H2, O2, N2, CO, CO2, H2O, and air." Trans. ASME 73:589–596 | Keyes |
| fay-riddell-stagnation-1958 | Fay–Riddell stagnation-point heating | stagnation_enthalpy, reynolds_number | Fay, J.A., Riddell, F.R. (1958). "Theory of stagnation point heat transfer in dissociated air." J. Aeronaut. Sci. 25(2):73–85 | Fay-Riddell |
| sutton-graves-stagnation-1971 | Sutton–Graves stagnation heating | stagnation_pressure, stagnation_enthalpy | Sutton, K., Graves, R.A. (1971). "A general stagnation-point convective-heating equation for arbitrary gas mixtures." NASA TR R-376 | Sutton-Graves |
| detra-kemp-riddell-1957 | Detra–Kemp–Riddell stagnation heating | stagnation_enthalpy, velocity_ratio | Detra, R.W., Kemp, N.H., Riddell, F.R. (1957). "Addendum to heat transfer to satellite vehicles re-entering the atmosphere." Jet Propulsion 27:1256–1257 | DKR |
| lees-hypersonic-heating-1956 | Lees laminar hypersonic heating distribution | mach_number, stagnation_enthalpy | Lees, L. (1956). "Laminar heat transfer over blunt-nosed bodies at hypersonic flight speeds." Jet Propulsion 26(4):259–269 | Lees |
| eckert-reference-enthalpy-1955 | Eckert reference-enthalpy method | mach_number, prandtl_number | Eckert, E.R.G. (1955). "Engineering relations for friction and heat transfer to surfaces in high velocity flow." J. Aeronaut. Sci. 22(8):585–587 | reference enthalpy |
| reshotko-en-transition-1962 | Reshotko e^N compressible transition | mach_number, reynolds_number | Reshotko, E. (1962). "Stability of the compressible laminar boundary layer." GALCIT Memo. 52 | Reshotko transition |
| simeonides-compressible-correlation-1996 | Simeonides compressible flat-plate heating | mach_number, reynolds_number | Simeonides, G. (1996). "Generalized reference-enthalpy formulations and simulation of viscous effects in hypersonic flow." Shock Waves 8(3):161–172 | Simeonides |
| zoby-engineering-heating-1981 | Zoby–Moss–Sutton engineering heating | reynolds_number, mach_number | Zoby, E.V., Moss, J.N., Sutton, K. (1981). "Approximate convective-heating equations for hypersonic flows." J. Spacecr. Rockets 18(1):64–70 | Zoby |

---

# Tranche 2 (combustion / species transport / rheology / rarefied)

## 10. combustion-kinetics  *(family already in `CLOSURE_FAMILIES`)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| westbrook-dryer-global-1981 | Westbrook–Dryer global hydrocarbon kinetics | equivalence_ratio, temperature | Westbrook, C.K., Dryer, F.L. (1981). "Simplified reaction mechanisms for the oxidation of hydrocarbon fuels in flames." Combust. Sci. Technol. 27(1–2):31–43 | Westbrook-Dryer |
| jones-lindstedt-global-1988 | Jones–Lindstedt 4-step global scheme | equivalence_ratio, temperature | Jones, W.P., Lindstedt, R.P. (1988). "Global reaction schemes for hydrocarbon combustion." Combust. Flame 73(3):233–249 | Jones-Lindstedt |
| magnussen-hjertager-ebu-1977 | Eddy-Break-Up / Eddy-Dissipation model | damkohler_number, turbulent_mixing_rate | Magnussen, B.F., Hjertager, B.H. (1977). "On mathematical modeling of turbulent combustion with special emphasis on soot formation and combustion." Symp. (Int.) Combust. 16(1):719–729 | EBU, eddy dissipation |
| magnussen-edc-1981 | Eddy-Dissipation Concept | reynolds_number, damkohler_number | Magnussen, B.F. (1981). "On the structure of turbulence and a generalized eddy dissipation concept for chemical reaction in turbulent flow." 19th AIAA Aerospace Sci. Meeting, AIAA-81-0042 | EDC |
| peters-flamelet-1984 | Laminar diffusion flamelet model | scalar_dissipation_rate, mixture_fraction | Peters, N. (1984). "Laminar diffusion flamelet models in non-premixed turbulent combustion." Prog. Energy Combust. Sci. 10(3):319–339 | flamelet |
| bray-moss-libby-1977 | BML premixed turbulent flame model | reaction_progress_variable | Bray, K.N.C., Moss, J.B. (1977). "A unified statistical model of the premixed turbulent flame." Acta Astronaut. 4(3–4):291–319 | BML |
| zimont-tfc-2000 | Zimont turbulent flame-speed closure | turbulence_intensity, laminar_flame_speed | Zimont, V.L. (2000). "Gas premixed combustion at high turbulence. Turbulent flame closure combustion model." Exp. Therm. Fluid Sci. 21(1–3):179–186 | TFC |
| metghalchi-keck-flame-speed-1982 | Metghalchi–Keck laminar flame speed | equivalence_ratio, pressure, temperature | Metghalchi, M., Keck, J.C. (1982). "Burning velocities of mixtures of air with methanol, isooctane, and indolene at high pressure and temperature." Combust. Flame 48:191–210 | Metghalchi-Keck |
| zeldovich-thermal-nox-1946 | Zeldovich thermal-NO mechanism | temperature, residence_time | Zeldovich, Y.B. (1946). "The oxidation of nitrogen in combustion and explosions." Acta Physicochim. URSS 21:577–628 | thermal NOx, Zeldovich |

## 11. species-diffusion  *(family already in `CLOSURE_FAMILIES`)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| chapman-enskog-diffusion-1939 | Chapman–Enskog binary gas diffusivity | temperature, pressure, lennard_jones_parameter | Chapman, S., Cowling, T.G. (1939). "The Mathematical Theory of Non-uniform Gases." Cambridge Univ. Press | Chapman-Enskog |
| fuller-schettler-giddings-1966 | Fuller gas-diffusivity correlation | temperature, pressure | Fuller, E.N., Schettler, P.D., Giddings, J.C. (1966). "A new method for prediction of binary gas-phase diffusion coefficients." Ind. Eng. Chem. 58(5):18–27 | Fuller |
| wilke-lee-diffusion-1955 | Wilke–Lee gas diffusivity | temperature, pressure | Wilke, C.R., Lee, C.Y. (1955). "Estimation of diffusion coefficients for gases and vapors." Ind. Eng. Chem. 47(6):1253–1257 | Wilke-Lee |
| wilke-chang-liquid-1955 | Wilke–Chang dilute-liquid diffusivity | temperature, viscosity | Wilke, C.R., Chang, P. (1955). "Correlation of diffusion coefficients in dilute solutions." AIChE J. 1(2):264–270 | Wilke-Chang |
| wilke-mixture-viscosity-1950 | Wilke gas-mixture viscosity rule | mole_fraction | Wilke, C.R. (1950). "A viscosity equation for gas mixtures." J. Chem. Phys. 18(4):517–519 | Wilke rule |
| hirschfelder-curtiss-bird-1954 | Hirschfelder–Curtiss–Bird transport (L-J) | temperature, lennard_jones_parameter | Hirschfelder, J.O., Curtiss, C.F., Bird, R.B. (1954). "Molecular Theory of Gases and Liquids." Wiley | HCB |
| stefan-maxwell-multicomponent-1871 | Stefan–Maxwell multicomponent diffusion | mole_fraction | Stefan, J. (1871). "Über das Gleichgewicht und die Bewegung, insbesondere die Diffusion von Gasgemengen." Sitzungsber. Akad. Wiss. Wien 63:63–124 | Stefan-Maxwell |

## 12. non-newtonian-rheology (additional)  *(family already in `CLOSURE_FAMILIES`; corpus has `casson-rheology-1959`)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| bingham-plastic-1916 | Bingham plastic | shear_rate, yield_stress | Bingham, E.C. (1916). "An investigation of the laws of plastic flow." Bull. Bur. Stand. 13:309–353 | Bingham |
| herschel-bulkley-1926 | Herschel–Bulkley yield-power-law | shear_rate, yield_stress | Herschel, W.H., Bulkley, R. (1926). "Konsistenzmessungen von Gummi-Benzollösungen." Kolloid-Z. 39(4):291–300 | Herschel-Bulkley |
| cross-viscosity-1965 | Cross pseudoplastic model | shear_rate | Cross, M.M. (1965). "Rheology of non-Newtonian fluids: a new flow equation for pseudoplastic systems." J. Colloid Sci. 20(5):417–437 | Cross |
| carreau-viscosity-1972 | Carreau model | shear_rate | Carreau, P.J. (1972). "Rheological equations from molecular network theories." Trans. Soc. Rheol. 16(1):99–127 | Carreau |
| carreau-yasuda-1981 | Carreau–Yasuda model (5-parameter) | shear_rate | Yasuda, K., Armstrong, R.C., Cohen, R.E. (1981). "Shear flow properties of concentrated solutions of linear and star branched polystyrenes." Rheol. Acta 20(2):163–178 | Carreau-Yasuda |
| sisko-viscosity-1958 | Sisko model | shear_rate | Sisko, A.W. (1958). "The flow of lubricating greases." Ind. Eng. Chem. 50(12):1789–1792 | Sisko |
| metzner-reed-generalized-re-1955 | Metzner–Reed generalized Reynolds number | generalized_reynolds_number, flow_behavior_index | Metzner, A.B., Reed, J.C. (1955). "Flow of non-newtonian fluids—correlation of the laminar, transition, and turbulent-flow regions." AIChE J. 1(4):434–440 | Metzner-Reed |
| dodge-metzner-turbulent-1959 | Dodge–Metzner turbulent friction (power-law) | generalized_reynolds_number, flow_behavior_index | Dodge, D.W., Metzner, A.B. (1959). "Turbulent flow of non-Newtonian systems." AIChE J. 5(2):189–204 | Dodge-Metzner |

## 13. rarefied-gas  *(NEW family name — author-approve; covers slip/jump + microscale)*

| closure_id | closure_name | coordinates | citation | aliases |
|---|---|---|---|---|
| maxwell-velocity-slip-1879 | Maxwell velocity-slip wall condition | knudsen_number | Maxwell, J.C. (1879). "On stresses in rarified gases arising from inequalities of temperature." Phil. Trans. R. Soc. 170:231–256 | Maxwell slip |
| smoluchowski-temperature-jump-1898 | Smoluchowski temperature-jump condition | knudsen_number | von Smoluchowski, M. (1898). "Über Wärmeleitung in verdünnten Gasen." Ann. Phys. 300(1):101–130 | temperature jump |
| deissler-second-order-slip-1964 | Deissler second-order slip/temperature-jump | knudsen_number | Deissler, R.G. (1964). "An analysis of second-order slip flow and temperature-jump boundary conditions for rarefied gases." Int. J. Heat Mass Transfer 7(6):681–694 | second-order slip |
| beskok-karniadakis-1999 | Beskok–Karniadakis unified slip model | knudsen_number | Beskok, A., Karniadakis, G.E. (1999). "A model for flows in channels, pipes, and ducts at micro and nano scales." Microscale Thermophys. Eng. 3(1):43–77 | Beskok-Karniadakis |
| bhatnagar-gross-krook-1954 | BGK kinetic collision model | knudsen_number | Bhatnagar, P.L., Gross, E.P., Krook, M. (1954). "A model for collision processes in gases. I." Phys. Rev. 94(3):511–525 | BGK |

---

## 14. Decisions (approved 2026-06-09)

1. **Family names — APPROVED.** Reused from the corpus `CLOSURE_FAMILIES` vocab (no validator change):
   `condensation`, `radiation`, `combustion-kinetics`, `species-diffusion`, `non-newtonian-rheology`,
   `single-phase-convection`. **NEW** family names approved: `external-convection`, `natural-convection`,
   `rarefied-gas`, and the §7-split families `hydraulic-friction`, `transfer-analogy`,
   `surface-enhancement` (renamed from "internal-enhancement"), `packed-porous`.
   - **Known debt (filed):** `external-convection` / `natural-convection` in the index map to the same
     physics the corpus files under `single-phase-convection`. Tolerable now (the index is metadata-only),
     but the eventual **corpus-family migration** is tracked so the two vocabularies don't drift silently.
2. **Count — both tranches kept.** After the fixes below: **147 new ≈ 200 total**. Marginal cost is near
   zero, and Tranche 2 signals the index covers CFD closures generally, not just heat-transfer correlations.
3. **Domain scope — cardio + aero IN.** Coverage-is-public is the ESDU posture; these two families are the
   storefront for the planned domain packs (the Taylor-thrombosis / Soares-platelet entries are exactly
   what a regulated-device prospect searches). All are case-2b until a vehicle curates bounds.
4. **Coordinate convention — bare `temperature` / `pressure`** chosen for absolute state variables
   (radiation's `gas_temperature` normalized to `temperature`). §15 reflects this.

### Entry corrections applied (pre-merge)

| was | fix |
|---|---|
| `grace-bubble-drag-1976` (cited Grace 1973 shapes/velocities) | → `grace-wairegi-nguyen-drag-1976`, cited to the GWN 1976 drag paper; id/name/citation aligned |
| `carreau-yasuda-blood-1979` (year/citation mismatch; Yasuda 1981 is polystyrene, not blood) | "blood" dropped; moved to §12 as generic `carreau-yasuda-1981`, properly cited |
| `tomiyama-wall-force-1998` (the 1998 "Struggle" paper is the *drag* citation = corpus `tomiyama-drag-1998`) | no clean distinct primary for the wall force → moved to §16 excluded |
| `zhukauskas-staggered-bank-1972` (dup citation, inconsistent transliteration, same closure) | merged into `zukauskas-tube-bank-1972` (note: inline & staggered) |
| `kays-crawford-turbulent-prandtl-1993` (id year ≠ 1994 citation) | → `kays-crawford-turbulent-prandtl-1994` |

## 15. New coordinate vocabulary introduced (for review)

These coordinates are NOT yet in the corpus and would be introduced (metadata-only, no bounds).
**Convention:** bare `temperature` / `pressure` for absolute state variables (contextualized ratio names
like `temperature_ratio_bulk_wall` stay as-is; `gas_temperature` was normalized to `temperature`).

Tranche 1: `film_reynolds_number, jakob_number, vapor_reynolds_number, equivalent_reynolds_number,
reduced_pressure, vapor_quality, martinelli_parameter, eotvos_number, morton_number,
particle_reynolds_number, pore_reynolds_number, void_fraction, porosity, turbulence_reynolds_number,
anisotropy_invariant, grid_filter_ratio, wall_distance, swirl_parameter, roughness_reynolds_number,
relative_roughness, graetz_number, peclet_number, schmidt_number, blending_exponent, fin_parameter,
optical_thickness, partial_pressure_path, shear_stress, shear_rate, exposure_time,
residence_time, hematocrit, stagnation_enthalpy, stagnation_pressure, temperature_ratio,
velocity_ratio`.

Tranche 2: `equivalence_ratio, damkohler_number, turbulent_mixing_rate, scalar_dissipation_rate,
mixture_fraction, reaction_progress_variable, turbulence_intensity, laminar_flame_speed, temperature,
pressure, mole_fraction, lennard_jones_parameter, viscosity, yield_stress, generalized_reynolds_number,
flow_behavior_index, knudsen_number`.

Index entries carry coordinate NAMES only (no bounds), so these are free to add; they become
load-bearing only if a future corpus entry curates a bound on one.

## 16. Excluded — uncertain attribution (per the no-placeholder rule)

Left OUT pending citation confirmation rather than guessed:
- **`tomiyama-wall-force-1998`** — the Eo-dependent wall force has no clean distinct primary (the 1998
  "Struggle" paper is the drag correlation, already `tomiyama-drag-1998` in the corpus). `antal-wall-force-1991`
  remains the curated wall-force entry; revisit if a verified Tomiyama/Hosokawa wall-force primary is confirmed.
- **"modified Gnielinski" supercritical variants** — multiple competing 2010s papers, attribution ambiguous.
- Proprietary solver wall-function blends (no primary citation) and textbook restatements without a clear
  primary source.
