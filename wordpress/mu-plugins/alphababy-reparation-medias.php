<?php
/**
 * Plugin Name: Alphababy - reparation des medias
 * Description: Ajoute un ecran « Outils, Reparation medias » qui detecte les images dont le fichier a change d'extension sur le disque et corrige la base. Analyse d'abord, repare seulement sur demande.
 * Version: 1.0.0
 * Author: SEO Monkey
 *
 * A deposer dans wp-content/mu-plugins/ puis aller dans Outils, Reparation medias.
 * Les mu-plugins s'activent seuls, il n'y a rien a activer.
 * Une fois la reparation faite, ce fichier peut etre supprime.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const ALPHABABY_RM_LOT = 150; // attachments traites par passage, evite les timeouts

/** Extensions candidates, dans l'ordre de recherche. */
function alphababy_rm_extensions() {
	return [
		'webp' => 'image/webp',
		'jpg'  => 'image/jpeg',
		'jpeg' => 'image/jpeg',
		'png'  => 'image/png',
		'gif'  => 'image/gif',
		'avif' => 'image/avif',
	];
}

/**
 * Examine un lot d'attachments.
 *
 * @param bool $appliquer Ecrit en base si vrai.
 * @param int  $offset    Position de depart.
 * @return array
 */
function alphababy_rm_examiner( $appliquer, $offset ) {
	$uploads = wp_get_upload_dir();
	$base    = $uploads['basedir'];
	$exts    = alphababy_rm_extensions();

	$ids = get_posts( [
		'post_type'      => 'attachment',
		'post_status'    => 'inherit',
		'post_mime_type' => 'image',
		'posts_per_page' => ALPHABABY_RM_LOT,
		'offset'         => $offset,
		'orderby'        => 'ID',
		'order'          => 'ASC',
		'fields'         => 'ids',
	] );

	$res = [ 'examines' => count( $ids ), 'recuperables' => [], 'perdus' => [], 'corriges' => 0 ];

	foreach ( $ids as $id ) {
		$relatif = get_post_meta( $id, '_wp_attached_file', true );
		if ( ! $relatif || file_exists( $base . '/' . $relatif ) ) {
			continue;
		}

		$sans_ext = preg_replace( '/\.[A-Za-z0-9]+$/', '', $relatif );
		$actuelle = strtolower( (string) pathinfo( $relatif, PATHINFO_EXTENSION ) );

		$trouvee = null;
		foreach ( array_keys( $exts ) as $ext ) {
			if ( $ext === $actuelle ) {
				continue;
			}
			if ( file_exists( $base . '/' . $sans_ext . '.' . $ext ) ) {
				$trouvee = $ext;
				break;
			}
		}

		$titre = get_the_title( $id );

		if ( null === $trouvee ) {
			$res['perdus'][] = [ 'id' => $id, 'titre' => $titre, 'fichier' => $relatif ];
			continue;
		}

		$nouveau = $sans_ext . '.' . $trouvee;
		$res['recuperables'][] = [ 'id' => $id, 'titre' => $titre, 'fichier' => $relatif, 'reel' => $nouveau ];

		if ( ! $appliquer ) {
			continue;
		}

		update_post_meta( $id, '_wp_attached_file', $nouveau );

		$meta = wp_get_attachment_metadata( $id );
		if ( is_array( $meta ) ) {
			$meta['file'] = $nouveau;
			$dossier      = dirname( $base . '/' . $nouveau );

			if ( ! empty( $meta['sizes'] ) && is_array( $meta['sizes'] ) ) {
				foreach ( $meta['sizes'] as $nom => $taille ) {
					if ( empty( $taille['file'] ) ) {
						continue;
					}
					$cand = preg_replace( '/\.[A-Za-z0-9]+$/', '.' . $trouvee, $taille['file'] );
					// On ne garde une taille que si son fichier existe vraiment :
					// une taille qui pointe dans le vide casse le srcset.
					if ( file_exists( $dossier . '/' . $cand ) ) {
						$meta['sizes'][ $nom ]['file']      = $cand;
						$meta['sizes'][ $nom ]['mime-type'] = $exts[ $trouvee ];
					} else {
						unset( $meta['sizes'][ $nom ] );
					}
				}
			}
			wp_update_attachment_metadata( $id, $meta );
		}

		wp_update_post( [ 'ID' => $id, 'post_mime_type' => $exts[ $trouvee ] ] );
		$res['corriges']++;
	}

	return $res;
}

/** Nombre total d'attachments image. */
function alphababy_rm_total() {
	$c = wp_count_attachments();
	$n = 0;
	foreach ( (array) $c as $mime => $nb ) {
		if ( 0 === strpos( (string) $mime, 'image/' ) ) {
			$n += (int) $nb;
		}
	}
	return $n;
}

add_action( 'admin_menu', function () {
	add_management_page(
		'Reparation medias',
		'Reparation medias',
		'manage_options',
		'alphababy-reparation-medias',
		'alphababy_rm_ecran'
	);
} );

function alphababy_rm_ecran() {
	if ( ! current_user_can( 'manage_options' ) ) {
		wp_die( 'Acces refuse.' );
	}

	$action    = isset( $_POST['alphababy_rm_action'] ) ? sanitize_key( $_POST['alphababy_rm_action'] ) : '';
	$offset    = isset( $_POST['offset'] ) ? max( 0, (int) $_POST['offset'] ) : 0;
	$total     = alphababy_rm_total();
	$resultat  = null;
	$appliquer = false;

	if ( $action && check_admin_referer( 'alphababy_rm' ) ) {
		$appliquer = ( 'reparer' === $action );
		$resultat  = alphababy_rm_examiner( $appliquer, $offset );
	}

	echo '<div class="wrap"><h1>Reparation des medias</h1>';

	echo '<p>Cet ecran cherche les images dont la base de donnees indique un fichier
	absent du disque, puis regarde si le meme fichier existe sous une autre
	extension. Si oui, il corrige la base. Sinon il le signale : un fichier absent
	du disque ne peut pas etre reconstruit ici, il faut le restaurer depuis une
	sauvegarde.</p>';

	printf( '<p><strong>%d</strong> images dans la mediatheque. Traitement par lots de %d.</p>',
		(int) $total, (int) ALPHABABY_RM_LOT );

	if ( null !== $resultat ) {
		$fin  = $offset + $resultat['examines'];
		$rec  = count( $resultat['recuperables'] );
		$perd = count( $resultat['perdus'] );

		echo '<div class="notice ' . ( $appliquer ? 'notice-success' : 'notice-info' ) . '"><p>';
		printf(
			'Lot %d a %d. %d reparables, %d sans fichier sur le disque. %s',
			(int) $offset + 1, (int) $fin, (int) $rec, (int) $perd,
			$appliquer
				? sprintf( '<strong>%d corriges en base.</strong>', (int) $resultat['corriges'] )
				: '<strong>Aucune ecriture, ceci est une analyse.</strong>'
		);
		echo '</p></div>';

		$tableau = function ( $titre, $lignes, $avec_reel ) {
			if ( ! $lignes ) {
				return;
			}
			echo '<h2>' . esc_html( $titre ) . ' (' . count( $lignes ) . ')</h2>';
			echo '<table class="widefat striped"><thead><tr><th>ID</th><th>Titre</th><th>Fichier declare en base</th>';
			if ( $avec_reel ) {
				echo '<th>Fichier reel sur le disque</th>';
			}
			echo '</tr></thead><tbody>';
			foreach ( $lignes as $l ) {
				echo '<tr><td>' . (int) $l['id'] . '</td><td>' . esc_html( $l['titre'] ) . '</td><td><code>'
					. esc_html( $l['fichier'] ) . '</code></td>';
				if ( $avec_reel ) {
					echo '<td><code>' . esc_html( $l['reel'] ) . '</code></td>';
				}
				echo '</tr>';
			}
			echo '</tbody></table>';
		};

		$tableau( 'Reparables', $resultat['recuperables'], true );
		$tableau( 'A restaurer depuis une sauvegarde', $resultat['perdus'], false );

		if ( $fin < $total ) {
			echo '<form method="post" style="margin-top:1em">';
			wp_nonce_field( 'alphababy_rm' );
			echo '<input type="hidden" name="offset" value="' . (int) $fin . '">';
			echo '<input type="hidden" name="alphababy_rm_action" value="' . esc_attr( $appliquer ? 'reparer' : 'analyser' ) . '">';
			submit_button( 'Continuer avec le lot suivant', 'primary', 'submit', false );
			echo '</form>';
		} else {
			echo '<p><strong>Fin de la mediatheque.</strong></p>';
		}
	}

	echo '<hr><h2>Lancer</h2>';
	echo '<form method="post" style="display:inline-block;margin-right:1em">';
	wp_nonce_field( 'alphababy_rm' );
	echo '<input type="hidden" name="offset" value="0">';
	echo '<input type="hidden" name="alphababy_rm_action" value="analyser">';
	submit_button( '1. Analyser sans rien modifier', 'secondary', 'submit', false );
	echo '</form>';

	echo '<form method="post" style="display:inline-block" onsubmit="return confirm(\'Confirmer la correction en base ? Une sauvegarde est recommandee avant.\');">';
	wp_nonce_field( 'alphababy_rm' );
	echo '<input type="hidden" name="offset" value="0">';
	echo '<input type="hidden" name="alphababy_rm_action" value="reparer">';
	submit_button( '2. Reparer', 'primary', 'submit', false );
	echo '</form>';

	echo '</div>';
}
