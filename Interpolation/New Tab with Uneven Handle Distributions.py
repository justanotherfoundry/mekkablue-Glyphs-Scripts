# MenuTitle: New Tab with Uneven Handle Distributions
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals
__doc__ = """
Finds glyphs where handle distributions change too much (e.g., from balanced to harmonised).
"""

import vanilla
from GlyphsApp import Glyphs, CURVE, Message, distance
from mekkablue import mekkaObject
from mekkablue.geometry import intersectionLineLinePoints, bezierWithPoints


class NewTabWithUnevenHandleDistributions(mekkaObject):
	prefDict = {
		"factorChange": 0,
		"factorChangeEntry": "2.5",
		"anyMaxToNotMax": 1,
		"markInFirstMaster": 0,
	}

	def __init__(self):
		# Window 'self.w':
		windowWidth = 310
		windowHeight = 170
		windowWidthResize = 100  # user can resize width by this value
		windowHeightResize = 0  # user can resize height by this value
		self.w = vanilla.FloatingWindow(
			(windowWidth, windowHeight),  # default window size
			"New Tab with Uneven Handle Distributions",  # window title
			minSize=(windowWidth, windowHeight),  # minimum size (for resizing)
			maxSize=(windowWidth + windowWidthResize, windowHeight + windowHeightResize),  # maximum size (for resizing)
			autosaveName=self.domain("mainwindow")  # stores last window position and size
		)

		# UI elements:
		linePos, inset, lineHeight = 12, 12, 22
		self.w.descriptionText = vanilla.TextBox((inset, linePos + 2, -inset, lineHeight * 2), "Finds compatible glyphs with curve segments in which the handle distribution changes too much:", sizeStyle='small', selectable=True)
		linePos += int(lineHeight * 1.8)

		self.w.factorChange = vanilla.CheckBox((inset, linePos, 230, 20), "Tolerated change factor (BCP1÷BCP2):", value=False, callback=self.SavePreferences, sizeStyle='small')
		self.w.factorChangeEntry = vanilla.EditText((inset + 230, linePos, -inset, 19), "2.5", callback=self.SavePreferences, sizeStyle='small')
		factorChangeTooltipText = "Calculates length ratios of handles in a curve segment in every master. If the ratio differs by more than the given factor in one or more masters, glyph will be reported."
		self.w.factorChange.getNSButton().setToolTip_(factorChangeTooltipText)
		self.w.factorChangeEntry.getNSTextField().setToolTip_(factorChangeTooltipText)
		linePos += lineHeight

		self.w.anyMaxToNotMax = vanilla.CheckBox((inset, linePos, -inset, 20), "Any handle that changes from 100% to non-100%", value=True, callback=self.SavePreferences, sizeStyle='small')
		self.w.anyMaxToNotMax.getNSButton().setToolTip_("Finds BCPs that are maximized (100%) in one master, but not in other masters.")
		linePos += lineHeight

		self.w.markInFirstMaster = vanilla.CheckBox((inset, linePos, -inset, 20), "Mark affected curve segments in first master", value=False, callback=self.SavePreferences, sizeStyle='small')
		self.w.markInFirstMaster.enable(False)
		self.w.markInFirstMaster.getNSButton().setToolTip_("Not implemented yet. Sorry.")
		linePos += lineHeight

		# Run Button:
		self.w.runButton = vanilla.Button((-100 - inset, -20 - inset, -inset, -inset), "Open Tab", sizeStyle='regular', callback=self.NewTabWithUnevenHandleDistributionsMain)
		self.w.setDefaultButton(self.w.runButton)

		# Load Settings:
		self.LoadPreferences()

		# Open window and focus on it:
		self.w.open()
		self.w.makeKey()

	def factor(self, A, B, C, D, intersection):
		handlePercentage1 = distance(A.position, B.position) / distance(A.position, intersection)
		handlePercentage2 = distance(D.position, C.position) / distance(D.position, intersection)
		return handlePercentage1 / handlePercentage2

	def factorChangeIsTooBig(self, maxFactorChange, firstFactor, pathIndex, indexA, indexB, indexC, indexD, otherLayers):
		for otherLayer in otherLayers:
			otherPath = otherLayer.paths[pathIndex]
			A = otherPath.nodes[indexA]
			B = otherPath.nodes[indexB]
			C = otherPath.nodes[indexC]
			D = otherPath.nodes[indexD]
			intersection = intersectionLineLinePoints(A.position, B.position, C.position, D.position)
			if intersection:
				otherFactor = self.factor(A, B, C, D, intersection)
				factorChange = otherFactor / firstFactor
				if factorChange > maxFactorChange or factorChange < 1 / maxFactorChange:
					return True
		return False

	def isMaxTheSameEverywhere(self, firstBCPsMaxed, pathIndex, indexA, indexB, indexC, indexD, otherLayers):
		for otherLayer in otherLayers:
			otherPath = otherLayer.paths[pathIndex]
			A = otherPath.nodes[indexA]
			B = otherPath.nodes[indexB]
			C = otherPath.nodes[indexC]
			D = otherPath.nodes[indexD]
			intersection = intersectionLineLinePoints(A.position, B.position, C.position, D.position)
			if intersection:
				BCPsMaxed = (B.position == intersection, C.position == intersection)
				if BCPsMaxed != firstBCPsMaxed:
					return False
		return True

	def insertMark(self, firstLayer, centerPoint):
		pass

	def NewTabWithUnevenHandleDistributionsMain(self, sender):
		try:
			# update settings to the latest user input:
			self.SavePreferences()

			thisFont = Glyphs.font  # frontmost font

			if not thisFont or not len(thisFont.masters) > 1:
				Message(
					title="Uneven Handle Distribution Error",
					message="This script requires a multiple-master font, because it measures the difference between BCP distributions of a curve segment in one master to the same curve in other masters.",
					OKButton="Oops, OK"
				)
			else:
				Glyphs.clearLog()
				print("New Tab with Uneven Handle Distributions\nReport for %s" % thisFont.familyName)
				if thisFont.filepath:
					print(thisFont.filepath)
				print()

				# query user options:
				shouldCheckFactorChange = self.pref("factorChange")
				maxFactorChange = self.prefFloat("factorChangeEntry")
				shouldCheckAnyMaxToNotMax = self.pref("anyMaxToNotMax")
				markInFirstMaster = self.pref("markInFirstMaster")

				glyphs = [g for g in thisFont.glyphs if g.mastersCompatible]
				print("Found %i compatible glyph%s." % (
					len(glyphs),
					"" if len(glyphs) == 1 else "s",
				))

				affectedGlyphs = []
				for thisGlyph in glyphs:
					firstLayer = thisGlyph.layers[0]
					if firstLayer.paths:
						otherLayers = [
							layer for layer in thisGlyph.layers if layer != firstLayer and (layer.isMasterLayer or layer.isSpecialLayer) and thisGlyph.mastersCompatibleForLayers_((layer, firstLayer))
						]
						for i, firstPath in enumerate(firstLayer.paths):
							if thisGlyph.name not in affectedGlyphs and not markInFirstMaster:
								for j, firstNode in enumerate(firstPath.nodes):
									if firstNode.type == CURVE:
										indexPrevNode = (j - 3) % len(firstPath.nodes)
										indexBCP1 = (j - 2) % len(firstPath.nodes)
										indexBCP2 = (j - 1) % len(firstPath.nodes)

										firstPrevNode = firstPath.nodes[indexPrevNode]
										firstBCP1 = firstPath.nodes[indexBCP1]
										firstBCP2 = firstPath.nodes[indexBCP2]

										firstIntersection = intersectionLineLinePoints(firstPrevNode, firstBCP1, firstBCP2, firstNode, includeMidBcp=True)
										if firstIntersection:
											if shouldCheckFactorChange:
												firstFactor = self.factor(firstPrevNode, firstBCP1, firstBCP2, firstNode, firstIntersection)
												if self.factorChangeIsTooBig(maxFactorChange, firstFactor, i, indexPrevNode, indexBCP1, indexBCP2, j, otherLayers):
													if thisGlyph.name not in affectedGlyphs:
														affectedGlyphs.append(thisGlyph.name)
													if markInFirstMaster:
														centerPoint = bezierWithPoints(firstPrevNode, firstBCP1, firstBCP2, firstNode, 0.5)
														self.insertMark(firstLayer, centerPoint)
													else:
														break
											if shouldCheckAnyMaxToNotMax:
												firstBCPsMaxed = (firstBCP1.position == firstIntersection, firstBCP2.position == firstIntersection)
												if not self.isMaxTheSameEverywhere(firstBCPsMaxed, i, indexPrevNode, indexBCP1, indexBCP2, j, otherLayers):
													if thisGlyph.name not in affectedGlyphs:
														affectedGlyphs.append(thisGlyph.name)
													if markInFirstMaster:
														centerPoint = bezierWithPoints(firstPrevNode, firstBCP1, firstBCP2, firstNode, 0.5)
														self.insertMark(firstLayer, centerPoint)
													else:
														break
				if affectedGlyphs:
					tabString = "/" + "/".join(affectedGlyphs)
					# opens new Edit tab:
					thisFont.newTab(tabString)
					print("Affected glyphs:\n%s" % tabString)
				else:
					# Floating notification:
					Glyphs.showNotification(
						"Handle Distribution %s" % (thisFont.familyName),
						"Found no uneven BCP distributions in the font.",
					)

				self.w.close()  # delete if you want window to stay open
		except Exception as e:
			# brings macro window to front and reports error:
			Glyphs.showMacroWindow()
			print("New Tab with Uneven Handle Distributions Error: %s" % e)
			import traceback
			print(traceback.format_exc())


NewTabWithUnevenHandleDistributions()
